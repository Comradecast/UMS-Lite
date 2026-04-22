from typing import Optional
import uuid
import sqlite3

from ums_lite.db.models import Match, MatchReport
from ums_lite.db.repositories import MatchRepo, ReportRepo

class MatchService:
    """
    Orchestration boundary for Match related actions.
    Ensures domain validation and advancement logic is applied before db writes.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.match_repo = MatchRepo(conn)
        self.report_repo = ReportRepo(conn)

    def report_match(self, match_id: uuid.UUID, reporter_id: str, claimed_winner_id: str) -> None:
        """Submit a match report and evaluate match resolution state."""
        pass

    def admin_force_win(self, match_id: uuid.UUID, admin_id: str, winner_id: str) -> None:
        """Force the outcome of a match as an admin."""
        pass
