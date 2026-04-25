from ums_lite.db.models import Tournament, TournamentState
from ums_lite.core.exceptions import InvalidStateError

def open_registration(tournament: Tournament) -> None:
    if tournament.state != TournamentState.DRAFT:
        raise InvalidStateError("You can only open registration from the Draft state.")
    tournament.state = TournamentState.REGISTRATION_OPEN

def close_registration(tournament: Tournament, entrant_count: int) -> None:
    if tournament.state != TournamentState.REGISTRATION_OPEN:
        raise InvalidStateError("You can only close registration when it is currently open.")
    if entrant_count < 2:
        raise InvalidStateError("You need at least 2 players before closing registration.")
    tournament.state = TournamentState.REGISTRATION_CLOSED

def start_tournament(tournament: Tournament, entrant_count: int) -> None:
    if tournament.state != TournamentState.REGISTRATION_CLOSED:
        raise InvalidStateError("You must close registration before starting the tournament.")
    if entrant_count < 2:
        raise InvalidStateError("You cannot start the tournament until at least 2 players have joined.")
    tournament.state = TournamentState.IN_PROGRESS

def complete_tournament(tournament: Tournament) -> None:
    if tournament.state != TournamentState.IN_PROGRESS:
        raise InvalidStateError("You can only complete a tournament that is currently in progress.")
    tournament.state = TournamentState.COMPLETED

def cancel_tournament(tournament: Tournament) -> None:
    if tournament.state in [TournamentState.COMPLETED, TournamentState.CANCELLED]:
        raise InvalidStateError("You cannot cancel a tournament that is already completed or cancelled.")
    tournament.state = TournamentState.CANCELLED
