import discord
from discord import app_commands
from discord.ext import commands

from ums_lite.db.database import db_session
from ums_lite.services.tournament_service import TournamentService
from ums_lite.core.exceptions import UMSCoreException

class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_service(self) -> TournamentService:
        # In a real app we might inject this properly per request,
        # but sharing the thread-local sqlite connection session wrapper is sufficient.
        return TournamentService(db_session.get_connection())

    # We use a group for /ums commands
    ums = app_commands.Group(name="ums", description="UMS Admin Commands")

    @ums.command(name="create", description="Create a new tournament")
    @app_commands.describe(name="The name of the tournament")
    @app_commands.default_permissions(manage_guild=True)
    async def create(self, interaction: discord.Interaction, name: str):
        if not interaction.guild_id:
            await interaction.response.send_message("This command must be run in a server.", ephemeral=True)
            return

        service = self._get_service()
        try:
            t = service.create_tournament(str(interaction.guild_id), name)
            await interaction.response.send_message(f"✅ Created tournament **{t.name}** in DRAFT state.", ephemeral=True)
        except UMSCoreException as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @ums.command(name="open", description="Open registration for the current draft tournament")
    @app_commands.default_permissions(manage_guild=True)
    async def open_registration(self, interaction: discord.Interaction):
        if not interaction.guild_id:
            return

        service = self._get_service()
        try:
            t = service.get_active_tournament(str(interaction.guild_id))
            if not t:
                await interaction.response.send_message("❌ No active tournament found.", ephemeral=True)
                return

            service.open_registration(t.id)
            await interaction.response.send_message(f"✅ Registration opened for **{t.name}**! Players can now join.", ephemeral=False)
        except UMSCoreException as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @ums.command(name="close", description="Close registration for the open tournament")
    @app_commands.default_permissions(manage_guild=True)
    async def close_registration(self, interaction: discord.Interaction):
        if not interaction.guild_id:
            return

        service = self._get_service()
        try:
            t = service.get_active_tournament(str(interaction.guild_id))
            if not t:
                await interaction.response.send_message("❌ No active tournament found.", ephemeral=True)
                return

            service.close_registration(t.id)
            await interaction.response.send_message(f"✅ Registration closed for **{t.name}**.", ephemeral=False)
        except UMSCoreException as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @ums.command(name="start", description="Generate bracket and start the tournament")
    @app_commands.default_permissions(manage_guild=True)
    async def start_tournament(self, interaction: discord.Interaction):
        if not interaction.guild_id:
            return

        service = self._get_service()
        try:
            t = service.get_active_tournament(str(interaction.guild_id))
            if not t:
                await interaction.response.send_message("❌ No active tournament found.", ephemeral=True)
                return

            matches = service.generate_bracket(t.id)
            await interaction.response.send_message(f"✅ Bracket generated with {len(matches)} matches! The tournament **{t.name}** has begun.", ephemeral=False)
        except UMSCoreException as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
