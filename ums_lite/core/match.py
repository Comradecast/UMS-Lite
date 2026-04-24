from typing import List, Optional
import uuid

from ums_lite.db.models import Match, MatchStatus, MatchReport
from ums_lite.core.exceptions import InvalidStateError

def submit_report(match: Match, existing_reports: List[MatchReport], new_report: MatchReport) -> None:
    """
    Handles state transitions for a match when a report is submitted.
    Updates the match entity in-place. The caller must persist the match and new_report.
    """
    if match.status not in [MatchStatus.ACTIVE, MatchStatus.AWAITING_CONFIRMATION]:
        raise InvalidStateError(f"Cannot submit report for a match that is already {match.status}.")

    if new_report.reporter_id not in [match.player1_id, match.player2_id]:
        raise InvalidStateError("You cannot report a match that is not assigned to you.")

    # Check if this player already reported
    if any(r.reporter_id == new_report.reporter_id for r in existing_reports):
        raise InvalidStateError("You have already reported this match.")

    all_reports = existing_reports + [new_report]

    if len(all_reports) == 1:
        # First report
        match.status = MatchStatus.AWAITING_CONFIRMATION
        return

    if len(all_reports) == 2:
        report1, report2 = all_reports

        # In a valid win/loss scenario, both players agree on who won.
        # e.g. P1 claims P1 won, P2 claims P1 won.
        if report1.claimed_winner_id == report2.claimed_winner_id:
            # Agreement!
            match.winner_id = report1.claimed_winner_id
            match.status = MatchStatus.RESOLVED
        else:
            # Conflict (Dispute)
            match.status = MatchStatus.DISPUTED
        return

    raise InvalidStateError("This match already has 2 reports. Cannot accept more.")

def advance_match_winner(match: Match, next_match: Optional[Match]) -> None:
    """
    Called when a match is resolved.
    Propagates the winner to the next match slot.
    Updates next_match in-place.
    """
    if match.status != MatchStatus.RESOLVED:
        raise InvalidStateError(f"Cannot advance winner from unresolved match {match.id}")

    if not match.winner_id:
        raise InvalidStateError(f"Resolved match {match.id} has no winner_id set.")

    if next_match is None:
        # Final match, nowhere to advance.
        return

    if next_match.id != match.next_match_id:
        raise ValueError("Provided next_match does not match the topology.")

    # Slot the winner in
    if match.next_match_slot == 1:
        next_match.player1_id = match.winner_id
    elif match.next_match_slot == 2:
        next_match.player2_id = match.winner_id
    else:
        raise ValueError(f"Invalid next_match_slot {match.next_match_slot}")

    # If the next match now has both players, it becomes active.
    if next_match.player1_id is not None and next_match.player2_id is not None:
        next_match.status = MatchStatus.ACTIVE
