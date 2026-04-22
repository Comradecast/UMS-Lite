from typing import Optional, List
import uuid
import sqlite3
from datetime import datetime, timezone

from ums_lite.db.models import Tournament, TournamentEntry, TournamentState, Match
from ums_lite.db.repositories import TournamentRepo, EntryRepo, PlayerRepo, MatchRepo
from ums_lite.core import tournament as tournament_domain
from ums_lite.core import bracket as bracket_domain
from ums_lite.core.exceptions import EntityNotFoundError, InvalidStateError

class TournamentService:
    """
    Orchestration boundary for Tournament related actions.
    Ensures domain validation is applied before db writes.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.tournament_repo = TournamentRepo(conn)
        self.entry_repo = EntryRepo(conn)
        self.player_repo = PlayerRepo(conn)
        self.match_repo = MatchRepo(conn)
        from ums_lite.db.repositories import GuildConfigRepo
        self.config_repo = GuildConfigRepo(conn)

    def get_guild_config(self, guild_id: str):
        from ums_lite.db.models import GuildConfig
        config = self.config_repo.get(guild_id)
        if not config:
            config = GuildConfig(guild_id=guild_id)
            with self.conn:
                self.config_repo.save(config)
        return config

    def toggle_elo_policy(self, guild_id: str) -> bool:
        with self.conn:
            config = self.get_guild_config(guild_id)
            config.elo_enabled = not config.elo_enabled
            self.config_repo.save(config)
            return config.elo_enabled

    def get_active_tournament(self, guild_id: str) -> Optional[Tournament]:
        return self.tournament_repo.get_active_by_guild(guild_id)

    def create_tournament(self, guild_id: str, name: str) -> Tournament:
        """Create a new tournament."""
        existing = self.tournament_repo.get_active_by_guild(guild_id)
        if existing:
            raise InvalidStateError("An active tournament already exists for this guild.")

        t = Tournament(
            id=uuid.uuid4(),
            guild_id=guild_id,
            name=name,
            state=TournamentState.DRAFT,
            created_at=datetime.now(timezone.utc)
        )
        with self.conn:
            self.tournament_repo.save(t)
        return t

    def open_registration(self, tournament_id: uuid.UUID) -> None:
        with self.conn:
            t = self.tournament_repo.get(tournament_id)
            if not t:
                raise EntityNotFoundError("Tournament not found")
            tournament_domain.open_registration(t)
            self.tournament_repo.save(t)

    def close_registration(self, tournament_id: uuid.UUID) -> None:
        with self.conn:
            t = self.tournament_repo.get(tournament_id)
            if not t:
                raise EntityNotFoundError("Tournament not found")
            tournament_domain.close_registration(t)
            self.tournament_repo.save(t)

    def join_tournament(self, tournament_id: uuid.UUID, discord_id: str) -> None:
        """Add a player to a tournament, handling rules and entity creation."""
        with self.conn:
            t = self.tournament_repo.get(tournament_id)
            if not t:
                raise EntityNotFoundError("Tournament not found")

            if t.state != TournamentState.REGISTRATION_OPEN:
                raise InvalidStateError("Registration is not open for this tournament.")

            # Verify/Create player record implicitly here
            p = self.player_repo.get(discord_id)
            if not p:
                from ums_lite.db.models import PlayerProfile
                p = PlayerProfile(discord_id=discord_id, username=f"User {discord_id}")
                self.player_repo.save(p)

            entry = TournamentEntry(
                id=uuid.uuid4(),
                tournament_id=tournament_id,
                player_id=discord_id,
                joined_at=datetime.now(timezone.utc)
            )
            # EntryRepo.create will throw DuplicateEntityError if already joined
            self.entry_repo.create(entry)

    def leave_tournament(self, tournament_id: uuid.UUID, discord_id: str) -> None:
        with self.conn:
            t = self.tournament_repo.get(tournament_id)
            if not t:
                raise EntityNotFoundError("Tournament not found")

            if t.state != TournamentState.REGISTRATION_OPEN:
                raise InvalidStateError("You can only leave during open registration.")

            self.entry_repo.delete_by_tournament_and_player(tournament_id, discord_id)

    def cancel_tournament(self, tournament_id: uuid.UUID) -> None:
        with self.conn:
            t = self.tournament_repo.get(tournament_id)
            if not t:
                raise EntityNotFoundError("Tournament not found")
            tournament_domain.cancel_tournament(t)
            self.tournament_repo.save(t)

    def generate_bracket(self, tournament_id: uuid.UUID) -> List[Match]:
        """Generate bracket and start tournament."""
        with self.conn:
            t = self.tournament_repo.get(tournament_id)
            if not t:
                raise EntityNotFoundError("Tournament not found")

            entries = self.entry_repo.get_by_tournament(tournament_id)
            entrant_count = len(entries)

            # Domain transition check
            tournament_domain.start_tournament(t, entrant_count)

            # Use deterministic order based on joined_at for seeding (simplest form)
            entries.sort(key=lambda e: e.joined_at)
            ordered_players = [e.player_id for e in entries]

            # Generate bracket
            matches = bracket_domain.generate_bracket(t.id, ordered_players)

            # Save everything
            self.tournament_repo.save(t)

            # Sort matches by round_number descending so that later rounds (which are
            # referenced by earlier rounds via next_match_id) are inserted into the DB first.
            # This satisfies the foreign key constraint `next_match_id -> matches(id)`.
            matches_to_save = sorted(matches, key=lambda m: m.round_number, reverse=True)
            for m in matches_to_save:
                self.match_repo.save(m)

            return matches
