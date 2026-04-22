import sqlite3
import uuid
from typing import List, Optional, TypeVar, Type, Any
from datetime import datetime

from ums_lite.db.models import (
    GuildConfig, PlayerProfile, Tournament, TournamentEntry,
    Match, MatchReport, AdminActionLog, TournamentState, MatchStatus
)
from ums_lite.core.exceptions import EntityNotFoundError, DuplicateEntityError

# Utility functions to handle SQLite UUIDs and Datetimes
def _parse_uuid(val: Optional[str]) -> Optional[uuid.UUID]:
    return uuid.UUID(val) if val else None

def _format_uuid(val: Optional[uuid.UUID]) -> Optional[str]:
    return str(val) if val else None

def _parse_datetime(val: str) -> datetime:
    return datetime.fromisoformat(val)

def _format_datetime(val: datetime) -> str:
    return val.isoformat()

class BaseRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        try:
            return self.conn.execute(query, params)
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise DuplicateEntityError(f"Duplicate entity error: {e}")
            raise # Other integrity errors (e.g., FK constraints) are left to surface

class GuildConfigRepo(BaseRepo):
    def get(self, guild_id: str) -> Optional[GuildConfig]:
        row = self._execute("SELECT * FROM guild_configs WHERE guild_id = ?", (guild_id,)).fetchone()
        if not row:
            return None
        return GuildConfig(
            guild_id=row['guild_id'],
            admin_role_id=row['admin_role_id'],
            participant_role_id=row['participant_role_id'],
            elo_enabled=bool(row['elo_enabled'])
        )

    def save(self, config: GuildConfig) -> None:
        self._execute(
            """
            INSERT INTO guild_configs (guild_id, admin_role_id, participant_role_id, elo_enabled)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                admin_role_id=excluded.admin_role_id,
                participant_role_id=excluded.participant_role_id,
                elo_enabled=excluded.elo_enabled
            """,
            (config.guild_id, config.admin_role_id, config.participant_role_id, int(config.elo_enabled))
        )

class PlayerRepo(BaseRepo):
    def get(self, discord_id: str) -> Optional[PlayerProfile]:
        row = self._execute("SELECT * FROM player_profiles WHERE discord_id = ?", (discord_id,)).fetchone()
        if not row:
            return None
        return PlayerProfile(
            discord_id=row['discord_id'],
            global_ums_id=_parse_uuid(row['global_ums_id']),
            username=row['username']
        )

    def save(self, player: PlayerProfile) -> None:
        self._execute(
            """
            INSERT INTO player_profiles (discord_id, global_ums_id, username)
            VALUES (?, ?, ?)
            ON CONFLICT(discord_id) DO UPDATE SET
                global_ums_id=excluded.global_ums_id,
                username=excluded.username
            """,
            (player.discord_id, _format_uuid(player.global_ums_id), player.username)
        )

class TournamentRepo(BaseRepo):
    def get(self, id: uuid.UUID) -> Optional[Tournament]:
        row = self._execute("SELECT * FROM tournaments WHERE id = ?", (_format_uuid(id),)).fetchone()
        if not row:
            return None
        return Tournament(
            id=_parse_uuid(row['id']),
            guild_id=row['guild_id'],
            name=row['name'],
            state=TournamentState(row['state']),
            created_at=_parse_datetime(row['created_at'])
        )

    def get_active_by_guild(self, guild_id: str) -> Optional[Tournament]:
        # Active is anything not COMPLETED or CANCELLED
        row = self._execute(
            "SELECT * FROM tournaments WHERE guild_id = ? AND state NOT IN (?, ?) ORDER BY created_at DESC LIMIT 1",
            (guild_id, TournamentState.COMPLETED.value, TournamentState.CANCELLED.value)
        ).fetchone()
        if not row:
            return None
        return Tournament(
            id=_parse_uuid(row['id']),
            guild_id=row['guild_id'],
            name=row['name'],
            state=TournamentState(row['state']),
            created_at=_parse_datetime(row['created_at'])
        )

    def save(self, tournament: Tournament) -> None:
        self._execute(
            """
            INSERT INTO tournaments (id, guild_id, name, state, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                state=excluded.state
            """,
            (
                _format_uuid(tournament.id),
                tournament.guild_id,
                tournament.name,
                tournament.state.value,
                _format_datetime(tournament.created_at)
            )
        )

class EntryRepo(BaseRepo):
    def get(self, id: uuid.UUID) -> Optional[TournamentEntry]:
        row = self._execute("SELECT * FROM tournament_entries WHERE id = ?", (_format_uuid(id),)).fetchone()
        if not row:
            return None
        return TournamentEntry(
            id=_parse_uuid(row['id']),
            tournament_id=_parse_uuid(row['tournament_id']),
            player_id=row['player_id'],
            joined_at=_parse_datetime(row['joined_at'])
        )

    def get_by_tournament(self, tournament_id: uuid.UUID) -> List[TournamentEntry]:
        rows = self._execute(
            "SELECT * FROM tournament_entries WHERE tournament_id = ?",
            (_format_uuid(tournament_id),)
        ).fetchall()

        return [TournamentEntry(
            id=_parse_uuid(row['id']),
            tournament_id=_parse_uuid(row['tournament_id']),
            player_id=row['player_id'],
            joined_at=_parse_datetime(row['joined_at'])
        ) for row in rows]

    def create(self, entry: TournamentEntry) -> None:
        self._execute(
            """
            INSERT INTO tournament_entries (id, tournament_id, player_id, joined_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                _format_uuid(entry.id),
                _format_uuid(entry.tournament_id),
                entry.player_id,
                _format_datetime(entry.joined_at)
            )
        )

    def delete(self, id: uuid.UUID) -> None:
        self._execute("DELETE FROM tournament_entries WHERE id = ?", (_format_uuid(id),))

    def delete_by_tournament_and_player(self, tournament_id: uuid.UUID, player_id: str) -> None:
        self._execute(
            "DELETE FROM tournament_entries WHERE tournament_id = ? AND player_id = ?",
            (_format_uuid(tournament_id), player_id)
        )

class MatchRepo(BaseRepo):
    def get(self, id: uuid.UUID) -> Optional[Match]:
        row = self._execute("SELECT * FROM matches WHERE id = ?", (_format_uuid(id),)).fetchone()
        if not row:
            return None
        return Match(
            id=_parse_uuid(row['id']),
            tournament_id=_parse_uuid(row['tournament_id']),
            round_number=row['round_number'],
            match_number=row['match_number'],
            player1_id=row['player1_id'],
            player2_id=row['player2_id'],
            winner_id=row['winner_id'],
            status=MatchStatus(row['status']),
            next_match_id=_parse_uuid(row['next_match_id']),
            next_match_slot=row['next_match_slot']
        )

    def get_active_by_player(self, tournament_id: uuid.UUID, player_id: str) -> Optional[Match]:
        row = self._execute(
            """
            SELECT * FROM matches
            WHERE tournament_id = ?
              AND status IN (?, ?)
              AND (player1_id = ? OR player2_id = ?)
            LIMIT 1
            """,
            (_format_uuid(tournament_id), MatchStatus.ACTIVE.value, MatchStatus.AWAITING_CONFIRMATION.value, player_id, player_id)
        ).fetchone()

        if not row:
            return None

        return Match(
            id=_parse_uuid(row['id']),
            tournament_id=_parse_uuid(row['tournament_id']),
            round_number=row['round_number'],
            match_number=row['match_number'],
            player1_id=row['player1_id'],
            player2_id=row['player2_id'],
            winner_id=row['winner_id'],
            status=MatchStatus(row['status']),
            next_match_id=_parse_uuid(row['next_match_id']),
            next_match_slot=row['next_match_slot']
        )

    def get_by_tournament(self, tournament_id: uuid.UUID) -> List[Match]:
        rows = self._execute(
            "SELECT * FROM matches WHERE tournament_id = ? ORDER BY round_number, match_number",
            (_format_uuid(tournament_id),)
        ).fetchall()

        return [Match(
            id=_parse_uuid(row['id']),
            tournament_id=_parse_uuid(row['tournament_id']),
            round_number=row['round_number'],
            match_number=row['match_number'],
            player1_id=row['player1_id'],
            player2_id=row['player2_id'],
            winner_id=row['winner_id'],
            status=MatchStatus(row['status']),
            next_match_id=_parse_uuid(row['next_match_id']),
            next_match_slot=row['next_match_slot']
        ) for row in rows]

    def save(self, match: Match) -> None:
        self._execute(
            """
            INSERT INTO matches (id, tournament_id, round_number, match_number, player1_id, player2_id, winner_id, status, next_match_id, next_match_slot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                player1_id=excluded.player1_id,
                player2_id=excluded.player2_id,
                winner_id=excluded.winner_id,
                status=excluded.status,
                next_match_id=excluded.next_match_id,
                next_match_slot=excluded.next_match_slot
            """,
            (
                _format_uuid(match.id),
                _format_uuid(match.tournament_id),
                match.round_number,
                match.match_number,
                match.player1_id,
                match.player2_id,
                match.winner_id,
                match.status.value,
                _format_uuid(match.next_match_id),
                match.next_match_slot
            )
        )

class ReportRepo(BaseRepo):
    def get_by_match(self, match_id: uuid.UUID) -> List[MatchReport]:
        rows = self._execute(
            "SELECT * FROM match_reports WHERE match_id = ? ORDER BY reported_at ASC",
            (_format_uuid(match_id),)
        ).fetchall()

        return [MatchReport(
            id=_parse_uuid(row['id']),
            match_id=_parse_uuid(row['match_id']),
            reporter_id=row['reporter_id'],
            claimed_winner_id=row['claimed_winner_id'],
            reported_at=_parse_datetime(row['reported_at'])
        ) for row in rows]

    def create(self, report: MatchReport) -> None:
        self._execute(
            """
            INSERT INTO match_reports (id, match_id, reporter_id, claimed_winner_id, reported_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                _format_uuid(report.id),
                _format_uuid(report.match_id),
                report.reporter_id,
                report.claimed_winner_id,
                _format_datetime(report.reported_at)
            )
        )

class AdminLogRepo(BaseRepo):
    def create(self, log: AdminActionLog) -> None:
        self._execute(
            """
            INSERT INTO admin_action_logs (id, guild_id, admin_id, action_type, target_entity_id, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _format_uuid(log.id),
                log.guild_id,
                log.admin_id,
                log.action_type,
                _format_uuid(log.target_entity_id),
                log.details,
                _format_datetime(log.timestamp)
            )
        )
