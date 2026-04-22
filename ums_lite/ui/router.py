import discord
import logging
from typing import Optional, Tuple

from ums_lite.db.database import db_session
from ums_lite.services.tournament_service import TournamentService
from ums_lite.services.match_service import MatchService
from ums_lite.db.models import TournamentState, MatchStatus

logger = logging.getLogger(__name__)

async def handle_ums_command(interaction: discord.Interaction):
    """
    Primary entry point for `/ums`.
    Strict priority:
    1. Active match exists -> Show Match Card
    2. User is admin -> Show Admin Control Panel
    3. Fallback -> Public Tournament Panel
    """
    if not interaction.guild_id:
        await interaction.response.send_message("Must be run in a server.", ephemeral=True)
        return

    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)

    conn = db_session.get_connection()
    t_service = TournamentService(conn)
    m_service = MatchService(conn)

    active_t = t_service.get_active_tournament(guild_id)
    is_admin = interaction.user.guild_permissions.manage_guild

    # Priority 1: Match Card
    if active_t and active_t.state == TournamentState.IN_PROGRESS:
        active_match = m_service.get_active_match(active_t.id, user_id)
        if active_match:
            from ums_lite.ui.match_views import MatchCard
            embed = _build_match_card_embed(active_match)
            view = MatchCard(active_match.id)

            # We must use a single persistent message for the match so both players see state transitions.
            await _render_persistent_match_card(interaction, active_match, embed, view, m_service)
            return

    # Priority 2: Admin Panel
    if is_admin:
        from ums_lite.ui.panels import AdminControlPanel
        config = t_service.get_guild_config(guild_id)
        embed = _build_admin_panel_embed(active_t, t_service, config)
        view = AdminControlPanel(guild_id, active_t)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        return

    # Priority 3: Public Tournament Panel
    from ums_lite.ui.panels import PublicTournamentPanel
    embed, view = _build_public_panel(active_t, t_service, user_id)

    # Render persistent panel logic
    await _render_persistent_public_panel(interaction, active_t, embed, view, t_service)

async def _render_persistent_public_panel(interaction: discord.Interaction, active_t, embed: discord.Embed, view: Optional[discord.ui.View], t_service: TournamentService):
    """
    Ensures the public panel is persistent.
    If it exists, edits it. If missing/deleted, sends a new one and saves the ID.
    If there is no active tournament, just send a basic ephemeral fallback.
    """
    if not active_t:
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    channel_id_str = active_t.panel_channel_id
    msg_id_str = active_t.panel_message_id

    recreate = False

    # We want public panels to be visible to everyone. If a user runs `/ums`, we don't want to spam the channel with new messages.
    # We edit the existing message if we can, then just acknowledge the interaction ephemerally.
    if channel_id_str and msg_id_str:
        channel = interaction.client.get_channel(int(channel_id_str))
        if channel:
            try:
                msg = await channel.fetch_message(int(msg_id_str))
                await msg.edit(embed=embed, view=view)

                # Acknowledge the user interaction
                if not interaction.response.is_done():
                    await interaction.response.send_message("The public tournament panel has been updated above.", ephemeral=True)
                return
            except discord.NotFound:
                recreate = True
            except discord.HTTPException as e:
                logger.error(f"Error editing panel: {e}")
                recreate = True
        else:
            recreate = True
    else:
        recreate = True

    if recreate:
        # Send new public message in the channel where the command was run
        if not interaction.response.is_done():
            # We must acknowledge the interaction. Sending a non-ephemeral response counts.
            msg = await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
            if not msg:
                # If interaction response doesn't return the message object in this context (often true for send_message),
                # we use followup or interaction.original_response()
                msg = await interaction.original_response()

            active_t.panel_channel_id = str(interaction.channel.id)
            active_t.panel_message_id = str(msg.id)

            with t_service.conn:
                t_service.tournament_repo.save(active_t)
        else:
            # Interaction already done (e.g. from a background sync or button callback fallback)
            msg = await interaction.channel.send(embed=embed, view=view)
            active_t.panel_channel_id = str(interaction.channel.id)
            active_t.panel_message_id = str(msg.id)
            with t_service.conn:
                t_service.tournament_repo.save(active_t)

async def _render_persistent_match_card(interaction: discord.Interaction, match, embed: discord.Embed, view: discord.ui.View, m_service: MatchService):
    channel_id_str = match.message_channel_id
    msg_id_str = match.message_id

    recreate = False

    if channel_id_str and msg_id_str:
        channel = interaction.client.get_channel(int(channel_id_str))
        if channel:
            try:
                msg = await channel.fetch_message(int(msg_id_str))
                await msg.edit(embed=embed, view=view)

                # Acknowledge the user interaction so it doesn't hang
                if not interaction.response.is_done():
                    await interaction.response.send_message("The match card has been updated above.", ephemeral=True)
                return
            except discord.NotFound:
                recreate = True
            except discord.HTTPException as e:
                logger.error(f"Error editing match card: {e}")
                recreate = True
        else:
            recreate = True
    else:
        recreate = True

    if recreate:
        # Send a new non-ephemeral message so both players can interact with the same exact UI component.
        if not interaction.response.is_done():
            msg = await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
            if not msg:
                msg = await interaction.original_response()

            match.message_channel_id = str(interaction.channel.id)
            match.message_id = str(msg.id)

            with m_service.conn:
                m_service.match_repo.save(match)
        else:
            msg = await interaction.channel.send(embed=embed, view=view)
            match.message_channel_id = str(interaction.channel.id)
            match.message_id = str(msg.id)
            with m_service.conn:
                m_service.match_repo.save(match)

async def sync_public_panel(client: discord.Client, guild_id: str):
    """
    Called by Admin or System workflows to forcibly update the public panel in-place
    without requiring a user interaction context.
    """
    conn = db_session.get_connection()
    t_service = TournamentService(conn)
    active_t = t_service.get_active_tournament(guild_id)

    if not active_t or not active_t.panel_channel_id or not active_t.panel_message_id:
        return

    from ums_lite.ui.panels import PublicTournamentPanel
    embed, view = _build_public_panel(active_t, t_service, None) # user_id None means default join button state for global render

    channel = client.get_channel(int(active_t.panel_channel_id))
    if channel:
        try:
            msg = await channel.fetch_message(int(active_t.panel_message_id))
            await msg.edit(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Failed to sync public panel: {e}")

# --- BUILDERS ---

def _build_match_card_embed(match) -> discord.Embed:
    embed = discord.Embed(
        title="🏆 Your Active Match",
        description=f"Round {match.round_number} | Match {match.match_number}\n\n**Status**: {match.status.value}",
        color=discord.Color.blue()
    )
    p1_display = f"<@{match.player1_id}>" if match.player1_id else "TBD / Bye"
    p2_display = f"<@{match.player2_id}>" if match.player2_id else "TBD / Bye"
    embed.add_field(name="Player 1", value=p1_display, inline=True)
    embed.add_field(name="Player 2", value=p2_display, inline=True)
    return embed

def _build_admin_panel_embed(active_t, t_service, config) -> discord.Embed:
    embed = discord.Embed(title="⚙️ UMS Admin Control Panel", color=discord.Color.dark_grey())
    if active_t:
        entries = t_service.entry_repo.get_by_tournament(active_t.id)
        embed.add_field(name="Tournament", value=active_t.name, inline=False)
        embed.add_field(name="State", value=active_t.state.value, inline=True)
        embed.add_field(name="Entrants", value=str(len(entries)), inline=True)
    else:
        embed.description = "No active tournament."

    embed.add_field(name="Elo Policy", value="Enabled" if config.elo_enabled else "Disabled", inline=False)
    return embed

def _build_public_panel(active_t, t_service, user_id: Optional[str]) -> Tuple[discord.Embed, Optional[discord.ui.View]]:
    from ums_lite.ui.panels import PublicTournamentPanel

    if not active_t:
        return discord.Embed(title="🏆 UMS Lite", description="No tournament is currently running.", color=discord.Color.light_grey()), None

    entries = t_service.entry_repo.get_by_tournament(active_t.id)
    is_joined = False
    if user_id:
        is_joined = any(e.player_id == user_id for e in entries)

    embed = discord.Embed(title=f"🏆 {active_t.name}", color=discord.Color.gold())
    embed.add_field(name="Status", value=active_t.state.value, inline=True)
    embed.add_field(name="Entrants", value=str(len(entries)), inline=True)

    if active_t.state == TournamentState.REGISTRATION_OPEN:
        embed.description = "Registration is currently open!"
    elif active_t.state == TournamentState.IN_PROGRESS:
        embed.description = "The tournament is currently underway!"
    else:
        embed.description = "The tournament is currently closed for registration."

    view = PublicTournamentPanel(active_t, is_joined)
    return embed, view
