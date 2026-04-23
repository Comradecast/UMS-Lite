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
        from ums_lite.db.repositories import PlayerRepo
        self.player_repo = PlayerRepo(conn)

    def get_active_match(self, tournament_id: uuid.UUID, player_id: str) -> Optional[Match]:
        return self.match_repo.get_active_by_player(tournament_id, player_id)

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
                self._handle_resolved_match(match)

            self.match_repo.save(match)

    def _handle_resolved_match(self, match: Match) -> None:
        """
        Updates player statistics and advances the bracket topology.
        Must be called within a transaction.
        """
        if match.status != MatchStatus.RESOLVED:
            return

        # Update stats if this was a played match (not a bye)
        if match.player1_id and match.player2_id and match.winner_id:
            p1 = self.player_repo.get(match.player1_id)
            p2 = self.player_repo.get(match.player2_id)

            if p1 and p2:
                p1.matches_played += 1
                p2.matches_played += 1

                if match.winner_id == p1.discord_id:
                    p1.wins += 1
                    p2.losses += 1
                elif match.winner_id == p2.discord_id:
                    p2.wins += 1
                    p1.losses += 1

                self.player_repo.save(p1)
                self.player_repo.save(p2)

        # Advance topology
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

    def admin_force_win(self, match_id: uuid.UUID, guild_id: str, admin_id: str, winner_id: str) -> None:
        """Force the outcome of a match as an admin, bypassing normal reporting rules."""
        with self.conn:
            match = self.match_repo.get(match_id)
            if not match:
                raise EntityNotFoundError("Match not found")

            if match.status == MatchStatus.RESOLVED:
                raise InvalidStateError("Match is already resolved.")

            if winner_id not in [match.player1_id, match.player2_id]:
                raise InvalidStateError(f"User {winner_id} is not part of this match.")

            # Log the admin action
            from ums_lite.db.models import AdminActionLog
            from ums_lite.db.repositories import AdminLogRepo
            import json

            admin_repo = AdminLogRepo(self.conn)
            log = AdminActionLog(
                id=uuid.uuid4(),
                guild_id=guild_id,
                admin_id=admin_id,
                action_type="FORCE_WIN",
                target_entity_id=match_id,
                details=json.dumps({"winner_id": winner_id, "previous_status": match.status.value}),
                timestamp=datetime.now(timezone.utc)
            )
            admin_repo.create(log)

            # Resolve
            match.winner_id = winner_id
            match.status = MatchStatus.RESOLVED

            self._handle_resolved_match(match)
            self.match_repo.save(match)
