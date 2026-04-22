from typing import Optional
import uuid
import sqlite3
from datetime import datetime, timezone

from ums_lite.db.models import Match, MatchReport, MatchStatus, TournamentState
from ums_lite.db.repositories import MatchRepo, ReportRepo, TournamentRepo
from ums_lite.core import match as match_domain
from ums_lite.core import tournament as tournament_domain
from ums_lite.core.exceptions import EntityNotFoundError, InvalidStateError

class MatchService:
    """
    Orchestration boundary for Match related actions.
    Ensures domain validation and advancement logic is applied before db writes.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.match_repo = MatchRepo(conn)
        self.report_repo = ReportRepo(conn)
        self.tournament_repo = TournamentRepo(conn)

    def report_match(self, match_id: uuid.UUID, reporter_id: str, claimed_winner_id: str) -> None:
        """Submit a match report and evaluate match resolution state."""
        with self.conn:
            match = self.match_repo.get(match_id)
            if not match:
                raise EntityNotFoundError("Match not found")

            existing_reports = self.report_repo.get_by_match(match_id)

            new_report = MatchReport(
                id=uuid.uuid4(),
                match_id=match_id,
                reporter_id=reporter_id,
                claimed_winner_id=claimed_winner_id,
                reported_at=datetime.now(timezone.utc)
            )

            # Domain logic updates match in place
            match_domain.submit_report(match, existing_reports, new_report)

            self.report_repo.create(new_report)

            if match.status == MatchStatus.RESOLVED:
                # Need to advance winner to next match if applicable
                if match.next_match_id:
                    next_match = self.match_repo.get(match.next_match_id)
                    if not next_match:
                        raise EntityNotFoundError(f"Downstream match {match.next_match_id} not found in DB.")

                    match_domain.advance_match_winner(match, next_match)
                    self.match_repo.save(next_match)
                else:
                    # Final match resolved, tournament is complete.
                    t = self.tournament_repo.get(match.tournament_id)
                    if t:
                        tournament_domain.complete_tournament(t)
                        self.tournament_repo.save(t)

            self.match_repo.save(match)

    def admin_force_win(self, match_id: uuid.UUID, admin_id: str, winner_id: str) -> None:
        """Force the outcome of a match as an admin."""
        # For a later phase, out of scope for current test integration
        pass
