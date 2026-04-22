import discord
from discord.ui import View, Button
from typing import Optional
import uuid

from ums_lite.db.database import db_session
from ums_lite.services.tournament_service import TournamentService
from ums_lite.db.models import Tournament, TournamentState
from ums_lite.core.exceptions import UMSCoreException, DuplicateEntityError

# Deferred import for router to prevent circular dependencies
def _re_render(interaction):
    from ums_lite.ui.router import render_ui
    return render_ui(interaction)

class AdminControlPanel(View):
    def __init__(self, guild_id: str, active_t: Optional[Tournament]):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.active_t = active_t

        # Setup buttons dynamically based on state
        if not self.active_t:
            # We don't have modals set up, so for MVP we use a default name for create
            btn_create = Button(label="Create Tournament", style=discord.ButtonStyle.primary, custom_id="admin_create")
            btn_create.callback = self.create_callback
            self.add_item(btn_create)
        else:
            state = self.active_t.state

            if state == TournamentState.DRAFT:
                btn_open = Button(label="Open Registration", style=discord.ButtonStyle.success, custom_id="admin_open")
                btn_open.callback = self.open_callback
                self.add_item(btn_open)

            elif state == TournamentState.REGISTRATION_OPEN:
                btn_close = Button(label="Close Registration", style=discord.ButtonStyle.danger, custom_id="admin_close")
                btn_close.callback = self.close_callback
                self.add_item(btn_close)

            elif state == TournamentState.REGISTRATION_CLOSED:
                btn_start = Button(label="Generate & Start", style=discord.ButtonStyle.primary, custom_id="admin_start")
                btn_start.callback = self.start_callback
                self.add_item(btn_start)

            btn_cancel = Button(label="Cancel Tournament", style=discord.ButtonStyle.danger, custom_id="admin_cancel", row=1)
            btn_cancel.callback = self.cancel_callback
            self.add_item(btn_cancel)

        btn_toggle_elo = Button(label="Toggle Elo Policy", style=discord.ButtonStyle.secondary, custom_id="admin_toggle_elo", row=1)
        btn_toggle_elo.callback = self.toggle_elo_callback
        self.add_item(btn_toggle_elo)

        btn_refresh = Button(label="Refresh", style=discord.ButtonStyle.secondary, custom_id="admin_refresh", row=1)
        btn_refresh.callback = self.refresh_callback
        self.add_item(btn_refresh)

    def _get_service(self):
        return TournamentService(db_session.get_connection())

    async def _handle_callback(self, interaction: discord.Interaction, action):
        await interaction.response.defer(ephemeral=True)
        try:
            action()
        except UMSCoreException as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
        await _re_render(interaction)

    async def create_callback(self, interaction: discord.Interaction):
        # Fallback default name until modals are built
        await self._handle_callback(interaction, lambda: self._get_service().create_tournament(self.guild_id, "New Tournament"))

    async def open_callback(self, interaction: discord.Interaction):
        await self._handle_callback(interaction, lambda: self._get_service().open_registration(self.active_t.id))

    async def close_callback(self, interaction: discord.Interaction):
        await self._handle_callback(interaction, lambda: self._get_service().close_registration(self.active_t.id))

    async def start_callback(self, interaction: discord.Interaction):
        await self._handle_callback(interaction, lambda: self._get_service().generate_bracket(self.active_t.id))

    async def cancel_callback(self, interaction: discord.Interaction):
        await self._handle_callback(interaction, lambda: self._get_service().cancel_tournament(self.active_t.id))

    async def toggle_elo_callback(self, interaction: discord.Interaction):
        await self._handle_callback(interaction, lambda: self._get_service().toggle_elo_policy(self.guild_id))

    async def refresh_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await _re_render(interaction)


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

    def _get_service(self):
        return TournamentService(db_session.get_connection())

    async def _handle_callback(self, interaction: discord.Interaction, action):
        await interaction.response.defer(ephemeral=True)
        try:
            action()
        except DuplicateEntityError:
            pass # Ignore silent UI double clicks
        except UMSCoreException as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
        await _re_render(interaction)

    async def join_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        await self._handle_callback(interaction, lambda: self._get_service().join_tournament(self.active_t.id, user_id))

    async def leave_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        await self._handle_callback(interaction, lambda: self._get_service().leave_tournament(self.active_t.id, user_id))

    async def refresh_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await _re_render(interaction)
