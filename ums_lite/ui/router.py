import discord
from ums_lite.db.database import db_session
from ums_lite.services.tournament_service import TournamentService
from ums_lite.services.match_service import MatchService
from ums_lite.db.models import TournamentState

# We import from router indirectly or implement the UI factory function inside router.py

def get_ums_ui(interaction: discord.Interaction):
    """
    Role-aware stateless router. Determines what panel to show based on:
    1. Does the user have an active match? -> Show MatchCard
    2. Is the user an admin? -> Show AdminControlPanel
    3. Else -> Show PublicTournamentPanel
    """
    from ums_lite.ui.panels import AdminControlPanel, PublicTournamentPanel
    from ums_lite.ui.match_views import MatchCard

    if not interaction.guild_id:
        return discord.Embed(description="Must be run in a guild"), None

    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)

    conn = db_session.get_connection()
    t_service = TournamentService(conn)
    m_service = MatchService(conn)

    active_t = t_service.get_active_tournament(guild_id)

    # 1. Match Card
    if active_t and active_t.state == TournamentState.IN_PROGRESS:
        active_match = m_service.get_active_match(active_t.id, user_id)
        if active_match:
            view = MatchCard(active_match.id)
            embed = discord.Embed(
                title="🏆 Your Active Match",
                description=f"Round {active_match.round_number} | Match {active_match.match_number}\n\n**Status**: {active_match.status.value}",
                color=discord.Color.blue()
            )
            # Fetch opponent name if possible (or just ID for MVP)
            embed.add_field(name="Player 1", value=f"<@{active_match.player1_id}>", inline=True)
            embed.add_field(name="Player 2", value=f"<@{active_match.player2_id}>", inline=True)
            return embed, view

    # 2. Admin Control Panel
    # Check if admin (simplified for MVP: manage_guild permission)
    is_admin = interaction.user.guild_permissions.manage_guild
    if is_admin:
        config = t_service.get_guild_config(guild_id)

        embed = discord.Embed(title="⚙️ UMS Admin Control Panel", color=discord.Color.dark_grey())

        if active_t:
            entries = t_service.entry_repo.get_by_tournament(active_t.id)
            embed.add_field(name="Tournament", value=active_t.name, inline=False)
            embed.add_field(name="State", value=active_t.state.value, inline=True)
            embed.add_field(name="Entrants", value=str(len(entries)), inline=True)
        else:
            embed.description = "No active tournament."

        embed.add_field(name="Elo Policy", value="Enabled" if config.elo_enabled else "Disabled", inline=False)

        return embed, AdminControlPanel(guild_id, active_t)

    # 3. Public Tournament Panel
    if active_t:
        entries = t_service.entry_repo.get_by_tournament(active_t.id)
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

        return embed, PublicTournamentPanel(active_t, is_joined)

    embed = discord.Embed(title="🏆 UMS Lite", description="No tournament is currently running.", color=discord.Color.light_grey())
    return embed, None

async def render_ui(interaction: discord.Interaction):
    """Helper to cleanly render the UI via response or followup."""
    embed, view = get_ums_ui(interaction)

    if interaction.response.is_done():
        if view:
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.edit_original_response(embed=embed, view=None)
    else:
        if view:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
