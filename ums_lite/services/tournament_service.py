from typing import Optional
import uuid
import sqlite3

from ums_lite.db.models import Tournament, TournamentEntry
from ums_lite.db.repositories import TournamentRepo, EntryRepo, PlayerRepo

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

    def create_tournament(self, tournament: Tournament) -> None:
        """Create a new tournament."""
        pass

    def join_tournament(self, tournament_id: uuid.UUID, discord_id: str) -> None:
        """Add a player to a tournament, handling rules and entity creation."""
        pass

    def generate_bracket(self, tournament_id: uuid.UUID) -> None:
        """Lock registration and generate initial bracket matches."""
        pass
