import discord
from discord.ui import View, Button
from typing import Optional
import uuid

from ums_lite.db.database import db_session
from ums_lite.services.tournament_service import TournamentService
from ums_lite.db.models import Tournament, TournamentState
from ums_lite.core.exceptions import UMSCoreException, DuplicateEntityError

class TournamentDetailsModal(discord.ui.Modal, title='Edit Tournament Details'):
    t_name = discord.ui.TextInput(label='Name', max_length=100, required=True)
    t_time = discord.ui.TextInput(label='Scheduled Time (Optional)', placeholder='e.g., Friday 8PM EST', required=False, max_length=50)
    t_region = discord.ui.TextInput(label='Region (Optional)', placeholder='e.g., USE, USW, EU', required=False, max_length=50)

    def __init__(self, active_t: Tournament, parent_view: 'AdminControlPanel'):
        super().__init__()
        self.active_t = active_t
        self.parent_view = parent_view

        self.t_name.default = active_t.name
        if active_t.scheduled_start_time:
            self.t_time.default = active_t.scheduled_start_time
        if active_t.region:
            self.t_region.default = active_t.region

    async def on_submit(self, interaction: discord.Interaction):
        try:
            _get_service().update_tournament_metadata(
                self.active_t.id,
                self.t_name.value,
                self.t_time.value if self.t_time.value else None,
                self.t_region.value if self.t_region.value else None
            )
        except UMSCoreException as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
            return

        await self.parent_view._handle_callback(interaction, lambda: None)


class ChannelSetupView(discord.ui.View):
    def __init__(self, guild_id: str, parent_panel=None):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.parent_panel = parent_panel

        config = _get_service().get_guild_config(guild_id)

        self.reg_select = discord.ui.ChannelSelect(channel_types=[discord.ChannelType.text], placeholder="Select Registration Channel")
        self.reg_select.callback = self.on_select
        self.add_item(self.reg_select)

        self.match_select = discord.ui.ChannelSelect(channel_types=[discord.ChannelType.text], placeholder="Select Match Cards Channel")
        self.match_select.callback = self.on_select
        self.add_item(self.match_select)

        self.results_select = discord.ui.ChannelSelect(channel_types=[discord.ChannelType.text], placeholder="Select Results Channel (Optional)")
        self.results_select.callback = self.on_select
        self.add_item(self.results_select)

        btn_save = Button(label="Save Channels", style=discord.ButtonStyle.success, row=3)
        btn_save.callback = self.save_callback
        self.add_item(btn_save)

        btn_cancel = Button(label="Cancel", style=discord.ButtonStyle.secondary, row=3)
        btn_cancel.callback = self.cancel_callback
        self.add_item(btn_cancel)

    async def on_select(self, interaction: discord.Interaction):
        await interaction.response.defer()

    async def save_callback(self, interaction: discord.Interaction):
        config = _get_service().get_guild_config(self.guild_id)
        reg_id = str(self.reg_select.values[0].id) if self.reg_select.values else config.registration_channel_id
        match_id = str(self.match_select.values[0].id) if self.match_select.values else config.match_channel_id
        results_id = str(self.results_select.values[0].id) if self.results_select.values else config.results_channel_id

        if not reg_id or not match_id:
            await interaction.response.send_message("❌ You must select at least Registration and Match channels.", ephemeral=True)
            return

        try:
            _get_service().update_guild_channels(self.guild_id, reg_id, match_id, results_id or "")
        except UMSCoreException as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
            return

        if self.parent_panel:
            await self.parent_panel._handle_callback(interaction, lambda: None)
        else:
            embed = discord.Embed(
                title="✅ Setup Complete",
                description="The required operational channels are now configured.\n\nPlease run `/ums` again to open the Admin Control Panel.",
                color=discord.Color.green()
            )
            await interaction.response.edit_message(embed=embed, view=None)

    async def cancel_callback(self, interaction: discord.Interaction):
        if self.parent_panel:
            await self.parent_panel._handle_callback(interaction, lambda: None)
        else:
            embed = discord.Embed(
                title="⚠️ Setup Cancelled",
                description="Configuration cancelled. You must configure channels to use UMS Lite.\nRun `/ums` again to restart setup.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)


class GuildSetupPanel(discord.ui.View):
    """Rendered directly by the router if channels are not configured."""
    def __init__(self, guild_id: str):
        super().__init__(timeout=None)
        self.guild_id = guild_id

        btn_channels = Button(label="Set Channels", style=discord.ButtonStyle.primary, custom_id="setup_channels")
        btn_channels.callback = self.channels_callback
        self.add_item(btn_channels)

    async def channels_callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Configure Channels", description="Select the required operational channels.")
        config = _get_service().get_guild_config(self.guild_id)
        embed.add_field(name="Current Registration", value=f"<#{config.registration_channel_id}>" if config.registration_channel_id else "None")
        embed.add_field(name="Current Match", value=f"<#{config.match_channel_id}>" if config.match_channel_id else "None")
        embed.add_field(name="Current Results", value=f"<#{config.results_channel_id}>" if config.results_channel_id else "None")

        view = ChannelSetupView(self.guild_id, parent_panel=None)
        await interaction.response.edit_message(embed=embed, view=view)

def _get_service():
    return TournamentService(db_session.get_connection())

class AdminControlPanel(View):
    def __init__(self, guild_id: str, active_t: Optional[Tournament]):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.active_t = active_t

        if not self.active_t:
            btn_create = Button(label="Create Tournament", style=discord.ButtonStyle.primary, custom_id="admin_create")
            btn_create.callback = self.create_callback
            self.add_item(btn_create)
        else:
            state = self.active_t.state

            # Setup Actions (Available before start)
            if state in [TournamentState.DRAFT, TournamentState.REGISTRATION_OPEN]:
                btn_edit = Button(label="Edit Details", style=discord.ButtonStyle.secondary, custom_id="admin_edit", row=0)
                btn_edit.callback = self.edit_callback
                self.add_item(btn_edit)

                btn_channels = Button(label="Set Channels", style=discord.ButtonStyle.secondary, custom_id="admin_channels", row=0)
                btn_channels.callback = self.channels_callback
                self.add_item(btn_channels)

            # Flow Actions
            if state == TournamentState.DRAFT:
                btn_open = Button(label="Open Registration", style=discord.ButtonStyle.success, custom_id="admin_open", row=1)
                btn_open.callback = self.open_callback
                self.add_item(btn_open)

            elif state == TournamentState.REGISTRATION_OPEN:
                btn_close = Button(label="Close Registration", style=discord.ButtonStyle.danger, custom_id="admin_close", row=1)
                btn_close.callback = self.close_callback
                self.add_item(btn_close)

            elif state == TournamentState.REGISTRATION_CLOSED:
                btn_start = Button(label="Generate & Start", style=discord.ButtonStyle.primary, custom_id="admin_start", row=1)
                btn_start.callback = self.start_callback
                self.add_item(btn_start)

            btn_cancel = Button(label="Cancel Tournament", style=discord.ButtonStyle.danger, custom_id="admin_cancel", row=2)
            btn_cancel.callback = self.cancel_callback
            self.add_item(btn_cancel)

        btn_toggle_elo = Button(label="Toggle Elo Policy", style=discord.ButtonStyle.secondary, custom_id="admin_toggle_elo", row=2)
        btn_toggle_elo.callback = self.toggle_elo_callback
        self.add_item(btn_toggle_elo)

        btn_refresh = Button(label="Refresh", style=discord.ButtonStyle.secondary, custom_id="admin_refresh", row=2)
        btn_refresh.callback = self.refresh_callback
        self.add_item(btn_refresh)

    async def _handle_callback(self, interaction: discord.Interaction, action, sync_public=False, start_bracket=False):
        try:
            action()
        except UMSCoreException as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
            return

        # Re-render this specific admin panel in place
        from ums_lite.ui.router import _build_admin_panel_embed
        service = _get_service()
        active_t = service.get_active_tournament(self.guild_id)
        config = service.get_guild_config(self.guild_id)
        profile = service.get_player_profile(str(interaction.user.id))
        recent = service.get_recent_tournaments(self.guild_id)

        embed = _build_admin_panel_embed(active_t, service, config, profile, recent)
        view = AdminControlPanel(self.guild_id, active_t)

        # We edit the message the button was on (ephemeral)
        await interaction.response.edit_message(embed=embed, view=view)

        if sync_public:
            from ums_lite.ui.router import sync_public_panel
            await sync_public_panel(interaction.client, self.guild_id)

        if start_bracket and active_t:
            from ums_lite.ui.router import sync_match_card
            from ums_lite.services.match_service import MatchService
            m_service = MatchService(db_session.get_connection())
            active_matches = m_service.match_repo.get_all_active_by_tournament(active_t.id)
            for m in active_matches:
                await sync_match_card(interaction.client, m.id)

    async def create_callback(self, interaction: discord.Interaction):
        await self._handle_callback(interaction, lambda: _get_service().create_tournament(self.guild_id, "New Tournament"), sync_public=True)

    async def edit_callback(self, interaction: discord.Interaction):
        if self.active_t:
            await interaction.response.send_modal(TournamentDetailsModal(self.active_t, self))

    async def channels_callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Configure Channels", description="Select the required operational channels.")
        config = _get_service().get_guild_config(self.guild_id)
        embed.add_field(name="Current Registration", value=f"<#{config.registration_channel_id}>" if config.registration_channel_id else "None")
        embed.add_field(name="Current Match", value=f"<#{config.match_channel_id}>" if config.match_channel_id else "None")
        embed.add_field(name="Current Results", value=f"<#{config.results_channel_id}>" if config.results_channel_id else "None")

        view = ChannelSetupView(self.guild_id, parent_panel=self)
        await interaction.response.edit_message(embed=embed, view=view)

    async def open_callback(self, interaction: discord.Interaction):
        await self._handle_callback(interaction, lambda: _get_service().open_registration(self.active_t.id), sync_public=True)

    async def close_callback(self, interaction: discord.Interaction):
        await self._handle_callback(interaction, lambda: _get_service().close_registration(self.active_t.id), sync_public=True)

    async def start_callback(self, interaction: discord.Interaction):
        await self._handle_callback(interaction, lambda: _get_service().generate_bracket(self.active_t.id), sync_public=True, start_bracket=True)

    async def cancel_callback(self, interaction: discord.Interaction):
        # We must capture the ID before it gets cancelled so we can sync the cancelled state explicitly
        t_id = self.active_t.id

        async def wrapped_cancel():
            # First run the normal service call
            try:
                _get_service().cancel_tournament(t_id)
            except UMSCoreException as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
                return

            # Then explicitly sync the cancelled state to the public panel
            from ums_lite.ui.router import sync_public_panel
            await sync_public_panel(interaction.client, self.guild_id, tournament_id=t_id)

            # Re-render the admin panel in place
            from ums_lite.ui.router import _build_admin_panel_embed
            service = _get_service()
            active_t = service.get_active_tournament(self.guild_id) # Should be None now
            config = service.get_guild_config(self.guild_id)
            profile = service.get_player_profile(str(interaction.user.id))
            recent = service.get_recent_tournaments(self.guild_id)

            embed = _build_admin_panel_embed(active_t, service, config, profile, recent)
            view = AdminControlPanel(self.guild_id, active_t)
            await interaction.response.edit_message(embed=embed, view=view)

        await wrapped_cancel()

    async def toggle_elo_callback(self, interaction: discord.Interaction):
        await self._handle_callback(interaction, lambda: _get_service().toggle_elo_policy(self.guild_id))

    async def refresh_callback(self, interaction: discord.Interaction):
        # Refresh passes sync_public=True to explicitly act as a public panel recovery/sync tool
        await self._handle_callback(interaction, lambda: None, sync_public=True)


class PublicTournamentPanel(View):
    def __init__(self, active_t: Tournament, is_joined: bool):
        super().__init__(timeout=None)
        self.active_t = active_t
        self.is_joined = is_joined

        if self.active_t.state == TournamentState.REGISTRATION_OPEN:
            if not is_joined:
                btn_join = Button(label="Join", style=discord.ButtonStyle.success, custom_id="public_join")
                btn_join.callback = self.join_callback
                self.add_item(btn_join)
            else:
                btn_leave = Button(label="Leave", style=discord.ButtonStyle.danger, custom_id="public_leave")
                btn_leave.callback = self.leave_callback
                self.add_item(btn_leave)

        btn_refresh = Button(label="Refresh", style=discord.ButtonStyle.secondary, custom_id="public_refresh")
        btn_refresh.callback = self.refresh_callback
        self.add_item(btn_refresh)

    async def _handle_callback(self, interaction: discord.Interaction, action):
        try:
            action()
        except DuplicateEntityError:
            pass # Ignore silent double clicks
        except UMSCoreException as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
            return

        # If the user clicked the button on an ephemeral panel, re-render it for them locally
        if interaction.message and interaction.message.flags.ephemeral:
            from ums_lite.ui.router import _build_public_panel
            service = _get_service()
            embed, view = _build_public_panel(self.active_t, service, str(interaction.user.id))

            # Inject stats for the ephemeral view
            profile = service.get_player_profile(str(interaction.user.id))
            if profile:
                desc = embed.description or ""
                embed.description = f"📊 **Your Stats:** {profile.wins}W - {profile.losses}L ({profile.matches_played} Matches, {profile.tournaments_played} Tourneys)\n\n" + desc

            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.defer()

        # Always re-render the global public panel
        from ums_lite.ui.router import sync_public_panel
        await sync_public_panel(interaction.client, self.active_t.guild_id)

    async def join_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        await self._handle_callback(interaction, lambda: _get_service().join_tournament(self.active_t.id, user_id))

    async def leave_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        await self._handle_callback(interaction, lambda: _get_service().leave_tournament(self.active_t.id, user_id))

    async def refresh_callback(self, interaction: discord.Interaction):
        await self._handle_callback(interaction, lambda: None)
