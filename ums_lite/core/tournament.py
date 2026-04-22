from ums_lite.db.models import Tournament, TournamentState
from ums_lite.core.exceptions import InvalidStateError

def open_registration(tournament: Tournament) -> None:
    if tournament.state != TournamentState.DRAFT:
        raise InvalidStateError(f"Cannot open registration from state {tournament.state}")
    tournament.state = TournamentState.REGISTRATION_OPEN

def close_registration(tournament: Tournament) -> None:
    if tournament.state != TournamentState.REGISTRATION_OPEN:
        raise InvalidStateError(f"Cannot close registration from state {tournament.state}")
    tournament.state = TournamentState.REGISTRATION_CLOSED

def start_tournament(tournament: Tournament, entrant_count: int) -> None:
    if tournament.state != TournamentState.REGISTRATION_CLOSED:
        raise InvalidStateError(f"Cannot start tournament from state {tournament.state}")
    if entrant_count < 2:
        raise InvalidStateError("Cannot start tournament with fewer than 2 entrants.")
    tournament.state = TournamentState.IN_PROGRESS

def complete_tournament(tournament: Tournament) -> None:
    if tournament.state != TournamentState.IN_PROGRESS:
        raise InvalidStateError(f"Cannot complete tournament from state {tournament.state}")
    tournament.state = TournamentState.COMPLETED

def cancel_tournament(tournament: Tournament) -> None:
    if tournament.state in [TournamentState.COMPLETED, TournamentState.CANCELLED]:
        raise InvalidStateError(f"Cannot cancel a tournament that is already {tournament.state}")
    tournament.state = TournamentState.CANCELLED
