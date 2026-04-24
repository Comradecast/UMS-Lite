import discord
import logging
import uuid
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
    profile = t_service.get_player_profile(user_id)
    config = t_service.get_guild_config(guild_id)

    # Preflight Check: Are operational channels configured?
    if not config.registration_channel_id or not config.match_channel_id:
        if is_admin:
            from ums_lite.ui.panels import GuildSetupPanel
            embed = discord.Embed(
                title="⚠️ Setup Required",
                description="UMS Lite is almost ready. You must configure the operational routing channels before tournaments can be managed.",
                color=discord.Color.red()
            )
            embed.add_field(name="Registration Channel", value=f"<#{config.registration_channel_id}>" if config.registration_channel_id else "❌ Missing")
            embed.add_field(name="Match Card Channel", value=f"<#{config.match_channel_id}>" if config.match_channel_id else "❌ Missing")

            view = GuildSetupPanel(guild_id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return
        else:
            await interaction.response.send_message("❌ This server has not finished configuring UMS Lite. Please ask an administrator to run `/ums` to complete setup.", ephemeral=True)
            return

    # Priority 1: Match Card
    if active_t and active_t.state == TournamentState.IN_PROGRESS:
        active_match = m_service.get_active_match(active_t.id, user_id)
        if active_match:
            from ums_lite.ui.match_views import MatchCard
            reports = m_service.report_repo.get_by_match(active_match.id)

            embed = _build_match_card_embed(active_match, reports)
            if profile:
                desc = embed.description or ""
                embed.description = f"📊 **Your Stats:** {profile.wins}W - {profile.losses}L ({profile.matches_played} Matches)\n\n" + desc

            view = MatchCard(active_match, is_admin)

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

            # Ensure shared match card exists by awaiting the sync explicitly
            await sync_match_card(interaction.client, active_match.id)
            return

    # Priority 2: Admin Panel
    if is_admin:
        from ums_lite.ui.panels import AdminControlPanel
        config = t_service.get_guild_config(guild_id)
        recent = t_service.get_recent_tournaments(guild_id)

        disputed_matches = []
        if active_t:
            disputed_matches = m_service.match_repo.get_disputed_matches(active_t.id)

        embed = _build_admin_panel_embed(active_t, t_service, config, profile, recent, disputed_matches)
        view = AdminControlPanel(guild_id, active_t)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        # Ensure shared public panel exists by awaiting the sync explicitly
        if active_t and active_t.state != TournamentState.DRAFT:
            await sync_public_panel(interaction.client, guild_id)
        return

    # Priority 3: Public Tournament Panel
    from ums_lite.ui.panels import PublicTournamentPanel

    embed, view = _build_public_panel(active_t, t_service, user_id)

    if profile:
        desc = embed.description or ""
        embed.description = f"📊 **Your Stats:** {profile.wins}W - {profile.losses}L ({profile.matches_played} Matches, {profile.tournaments_played} Tourneys)\n\n" + desc

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # Ensure shared public panel exists by awaiting the sync explicitly
    if active_t and active_t.state != TournamentState.DRAFT:
        await sync_public_panel(interaction.client, guild_id)

async def sync_public_panel(client: discord.Client, guild_id: str, tournament_id: Optional[uuid.UUID] = None):
    """
    Called by Admin or System workflows to forcibly update the shared, persistent public panel in-place.
    If the panel is missing, recreates it in the strictly configured registration channel.
    If tournament_id is provided, it specifically syncs that tournament (useful for terminal states like COMPLETED/CANCELLED).
    """
    conn = db_session.get_connection()
    t_service = TournamentService(conn)

    if tournament_id:
        active_t = t_service.tournament_repo.get(tournament_id)
    else:
        active_t = t_service.get_active_tournament(guild_id)

    if not active_t or active_t.state == TournamentState.DRAFT:
        return

    config = t_service.get_guild_config(guild_id)

    from ums_lite.ui.panels import PublicTournamentPanel
    embed, view = _build_public_panel(active_t, t_service, None) # user_id None means default join button state for global render

    # We always fallback explicitly to the config's registration_channel_id
    target_channel_id = active_t.panel_channel_id or config.registration_channel_id
    if not target_channel_id:
        return

    channel = client.get_channel(int(target_channel_id))
    if channel:
        try:
            if active_t.panel_message_id:
                msg = await channel.fetch_message(int(active_t.panel_message_id))
                await msg.edit(embed=embed, view=view)
                return
        except discord.NotFound:
            pass # We will recreate it below
        except Exception as e:
            logger.error(f"Failed to fetch public panel: {e}")
            return

        # Recovery or Initial Creation
        msg = await channel.send(embed=embed, view=view)
        active_t.panel_channel_id = str(channel.id)
        active_t.panel_message_id = str(msg.id)
        with t_service.conn:
            t_service.tournament_repo.save(active_t)

async def reconcile_active_messages(client: discord.Client):
    """
    Startup helper to reconcile persisted UI references.
    Iterates over all active tournaments to ensure public panels exist.
    Iterates over active/disputed matches to ensure match cards exist.
    """
    await client.wait_until_ready()
    conn = db_session.get_connection()
    t_repo = TournamentService(conn).tournament_repo
    m_repo = MatchService(conn).match_repo

    active_tournaments = t_repo.get_all_active()
    for t in active_tournaments:
        if t.panel_channel_id and t.panel_message_id:
            await sync_public_panel(client, t.guild_id)

        active_matches = m_repo.get_all_active_by_tournament(t.id)
        for m in active_matches:
            if m.message_channel_id and m.message_id:
                await sync_match_card(client, m.id)

async def sync_match_card(client: discord.Client, match_id: uuid.UUID):
    """
    Called by System workflows to forcibly update the shared, persistent match card in-place.
    If the card is missing, recreates it in the strictly configured match channel.
    """
    conn = db_session.get_connection()
    m_service = MatchService(conn)
    match = m_service.match_repo.get(match_id)

    if not match:
        return

    t_service = TournamentService(conn)
    t = t_service.tournament_repo.get(match.tournament_id)
    config = t_service.get_guild_config(t.guild_id) if t else None

    from ums_lite.ui.match_views import MatchCard
    reports = m_service.report_repo.get_by_match(match.id)
    embed = _build_match_card_embed(match, reports)

    # The shared card will render the dispute buttons for everyone if the match is DISPUTED.
    # The callback logic in MatchCard securely enforces admin-only usage for those buttons.
    view = MatchCard(match, is_admin=True) if match.status in [MatchStatus.ACTIVE, MatchStatus.AWAITING_CONFIRMATION, MatchStatus.DISPUTED] else None

    match_channel = config.match_channel_id if config else None
    target_channel_id = match.message_channel_id or match_channel
    if not target_channel_id:
        return

    channel = client.get_channel(int(target_channel_id))
    if channel:
        try:
            if match.message_id:
                msg = await channel.fetch_message(int(match.message_id))
                await msg.edit(embed=embed, view=view)
                return
        except discord.NotFound:
            pass # We will recreate it below
        except Exception as e:
            logger.error(f"Failed to fetch match card: {e}")
            return

        # Recovery or Initial Creation
        msg = await channel.send(embed=embed, view=view)
        match.message_channel_id = str(channel.id)
        match.message_id = str(msg.id)
        with m_service.conn:
            m_service.match_repo.save(match)

async def announce_tournament_results(client: discord.Client, tournament_id: uuid.UUID):
    conn = db_session.get_connection()
    t_service = TournamentService(conn)

    t = t_service.tournament_repo.get(tournament_id)
    if not t or t.state != TournamentState.COMPLETED or not t.results_channel_id:
        return

    winner = t_service.get_tournament_winner(tournament_id)
    if not winner:
        return

    config = t_service.get_guild_config(t.guild_id)
    if not config.results_channel_id:
        return

    channel = client.get_channel(int(config.results_channel_id))
    if not channel:
        return

    embed = discord.Embed(
        title=f"🏆 {t.name} Results",
        description=f"**Congratulations to the winner:** <@{winner}>!",
        color=discord.Color.gold()
    )
    try:
        await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Failed to announce tournament results: {e}")

# --- BUILDERS ---

def _build_match_card_embed(match, reports: list) -> discord.Embed:
    color = discord.Color.blue()
    if match.status == MatchStatus.AWAITING_CONFIRMATION:
        color = discord.Color.orange()
    elif match.status == MatchStatus.DISPUTED:
        color = discord.Color.red()
    elif match.status == MatchStatus.RESOLVED:
        color = discord.Color.green()

    embed = discord.Embed(
        title="🏆 Match Card",
        description=f"Round {match.round_number} | Match {match.match_number}\n\n**Status**: {match.status.value}",
        color=color
    )
    p1_display = f"<@{match.player1_id}>" if match.player1_id else "TBD / Bye"
    p2_display = f"<@{match.player2_id}>" if match.player2_id else "TBD / Bye"
    embed.add_field(name="Player 1", value=p1_display, inline=True)
    embed.add_field(name="Player 2", value=p2_display, inline=True)

    if reports:
        reports_text = ""
        for r in reports:
            reports_text += f"• <@{r.reporter_id}> claimed <@{r.claimed_winner_id}> won.\n"
        embed.add_field(name="Reports", value=reports_text, inline=False)

    if match.status == MatchStatus.RESOLVED and match.winner_id:
        embed.add_field(name="👑 Winner", value=f"<@{match.winner_id}>", inline=False)

    return embed

def _build_admin_panel_embed(active_t, t_service, config, profile=None, recent=None, disputed_matches=None) -> discord.Embed:
    embed = discord.Embed(title="⚙️ UMS Admin Control Panel", color=discord.Color.dark_grey())

    if profile:
        embed.description = f"**Your Stats:** {profile.wins}W - {profile.losses}L ({profile.matches_played} Matches, {profile.tournaments_played} Tourneys)"

    if active_t:
        entries = t_service.entry_repo.get_by_tournament(active_t.id)
        embed.add_field(name="Active Tournament", value=active_t.name, inline=False)
        embed.add_field(name="State", value=active_t.state.value, inline=True)
        embed.add_field(name="Entrants", value=str(len(entries)), inline=True)

        if disputed_matches:
            disputed_text = ""
            for m in disputed_matches:
                disputed_text += f"• Round {m.round_number} Match {m.match_number}: <@{m.player1_id}> vs <@{m.player2_id}>\n"
            embed.add_field(name="⚠️ Disputed Matches (Action Required)", value=disputed_text, inline=False)

        if active_t.state in [TournamentState.DRAFT, TournamentState.REGISTRATION_OPEN]:
            meta_text = f"**Scheduled:** {active_t.scheduled_start_time or 'TBD'}\n"
            meta_text += f"**Region:** {active_t.region or 'TBD'}\n"
            meta_text += f"**Format:** {active_t.format}\n"
            embed.add_field(name="Metadata", value=meta_text, inline=False)

        channels_text = f"**Registration:** <#{config.registration_channel_id}>" if config.registration_channel_id else "**Registration:** ❌ Missing"
        channels_text += f"\n**Match Cards:** <#{config.match_channel_id}>" if config.match_channel_id else "\n**Match Cards:** ❌ Missing"
        channels_text += f"\n**Results:** <#{config.results_channel_id}>" if config.results_channel_id else "\n**Results:** Optional"
        embed.add_field(name="Operational Channels", value=channels_text, inline=False)

    else:
        embed.add_field(name="Active Tournament", value="None running.", inline=False)

    embed.add_field(name="Elo Policy", value="Enabled" if config.elo_enabled else "Disabled", inline=False)

    if recent:
        recent_text = ""
        for t in recent:
            recent_text += f"• **{t.name}** ({t.state.value})\n"
        embed.add_field(name="Recent History", value=recent_text, inline=False)

    return embed

def _build_public_panel(active_t, t_service, user_id: Optional[str]) -> Tuple[discord.Embed, Optional[discord.ui.View]]:
    from ums_lite.ui.panels import PublicTournamentPanel

    if not active_t or active_t.state == TournamentState.DRAFT:
        return discord.Embed(title="🏆 UMS Lite", description="No tournament is currently running.", color=discord.Color.light_grey()), None

    embed = discord.Embed(title=f"🏆 {active_t.name}", color=discord.Color.gold())
    entries = t_service.entry_repo.get_by_tournament(active_t.id)
    is_joined = False
    if user_id:
        is_joined = any(e.player_id == user_id for e in entries)

    embed.add_field(name="Status", value=active_t.state.value, inline=True)
    embed.add_field(name="Entrants", value=str(len(entries)), inline=True)

    if active_t.state == TournamentState.REGISTRATION_OPEN:
        embed.description = "Registration is currently open!"
    elif active_t.state == TournamentState.IN_PROGRESS:
        embed.description = "The tournament is currently underway!"
    elif active_t.state == TournamentState.COMPLETED:
        embed.description = "The tournament is **COMPLETE**!"
        winner = t_service.get_tournament_winner(active_t.id)
        if winner:
            embed.add_field(name="🏆 Tournament Winner", value=f"<@{winner}>", inline=False)
    else:
        embed.description = "The tournament is currently closed for registration."

    view = PublicTournamentPanel(active_t, is_joined)
    return embed, view
