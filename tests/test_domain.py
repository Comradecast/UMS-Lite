import pytest
import uuid
from datetime import datetime

from ums_lite.db.models import Tournament, TournamentState, Match, MatchStatus, MatchReport
from ums_lite.core.tournament import (
    open_registration, close_registration, start_tournament,
    complete_tournament, cancel_tournament
)
from ums_lite.core.bracket import generate_bracket
from ums_lite.core.match import submit_report, advance_match_winner
from ums_lite.core.exceptions import InvalidStateError

# --- TOURNAMENT STATE TESTS ---

def test_valid_tournament_transitions():
    t = Tournament(id=uuid.uuid4(), guild_id="g1", name="Test", state=TournamentState.DRAFT, created_at=datetime.now())

    open_registration(t)
    assert t.state == TournamentState.REGISTRATION_OPEN

    close_registration(t)
    assert t.state == TournamentState.REGISTRATION_CLOSED

    start_tournament(t, entrant_count=2)
    assert t.state == TournamentState.IN_PROGRESS

    complete_tournament(t)
    assert t.state == TournamentState.COMPLETED

def test_invalid_start_not_enough_players():
    t = Tournament(id=uuid.uuid4(), guild_id="g1", name="Test", state=TournamentState.REGISTRATION_CLOSED, created_at=datetime.now())

    with pytest.raises(InvalidStateError, match="at least 2 players have joined"):
        start_tournament(t, entrant_count=1)

def test_invalid_transition_order():
    t = Tournament(id=uuid.uuid4(), guild_id="g1", name="Test", state=TournamentState.DRAFT, created_at=datetime.now())

    with pytest.raises(InvalidStateError):
        start_tournament(t, entrant_count=2) # Draft -> Start is invalid

    with pytest.raises(InvalidStateError):
        close_registration(t) # Draft -> Closed is invalid

def test_cancel_tournament():
    t = Tournament(id=uuid.uuid4(), guild_id="g1", name="Test", state=TournamentState.REGISTRATION_OPEN, created_at=datetime.now())
    cancel_tournament(t)
    assert t.state == TournamentState.CANCELLED

    with pytest.raises(InvalidStateError):
        cancel_tournament(t) # Already cancelled

# --- BRACKET GENERATION TESTS ---

def test_bracket_2_players():
    t_id = uuid.uuid4()
    players = ["P1", "P2"]

    matches = generate_bracket(t_id, players)

    assert len(matches) == 1
    m = matches[0]
    assert m.round_number == 1
    assert m.player1_id == "P1"
    assert m.player2_id == "P2"
    assert m.status == MatchStatus.ACTIVE
    assert m.next_match_id is None

def test_bracket_3_players_bye_handling():
    t_id = uuid.uuid4()
    players = ["P1", "P2", "P3"]
    # For 3 players, bracket size 4.
    # Byes = 4 - 3 = 1
    # P1 gets bye. P2 plays P3.

    matches = generate_bracket(t_id, players)

    # R1: M1(P1 v Bye), M2(P2 v P3)
    # R2: M3(Winner M1 v Winner M2)
    assert len(matches) == 3

    m1 = next(m for m in matches if m.round_number == 1 and m.player1_id == "P1")
    assert m1.player2_id is None
    assert m1.status == MatchStatus.RESOLVED
    assert m1.winner_id == "P1"

    m2 = next(m for m in matches if m.round_number == 1 and m.player1_id == "P2")
    assert m2.player2_id == "P3"
    assert m2.status == MatchStatus.ACTIVE

    m3 = next(m for m in matches if m.round_number == 2)
    assert m3.player1_id == "P1" # Advanced from bye
    assert m3.player2_id is None # Waiting for M2
    assert m3.status == MatchStatus.PENDING

    # Topology wiring check
    assert m1.next_match_id == m3.id
    assert m1.next_match_slot == 1
    assert m2.next_match_id == m3.id
    assert m2.next_match_slot == 2

def test_bracket_4_players():
    t_id = uuid.uuid4()
    players = ["P1", "P2", "P3", "P4"]

    matches = generate_bracket(t_id, players)
    assert len(matches) == 3 # 2 semi, 1 final

    # No byes
    for m in matches:
        if m.round_number == 1:
            assert m.status == MatchStatus.ACTIVE
            assert m.player1_id is not None
            assert m.player2_id is not None

def test_bracket_5_players():
    t_id = uuid.uuid4()
    players = ["P1", "P2", "P3", "P4", "P5"]

    # Size = 8, byes = 3
    # P1 vs Bye, P2 vs Bye, P3 vs Bye, P4 vs P5
    matches = generate_bracket(t_id, players)

    assert len(matches) == 7 # 4 quarters, 2 semis, 1 final

    r1_matches = [m for m in matches if m.round_number == 1]
    assert len(r1_matches) == 4

    resolved = [m for m in r1_matches if m.status == MatchStatus.RESOLVED]
    assert len(resolved) == 3

    active = [m for m in r1_matches if m.status == MatchStatus.ACTIVE]
    assert len(active) == 1
    assert active[0].player1_id == "P4"
    assert active[0].player2_id == "P5"

def test_bracket_invalid_players():
    with pytest.raises(ValueError):
        generate_bracket(uuid.uuid4(), ["P1"])

# --- MATCH RESOLUTION TESTS ---

def test_valid_match_agreement():
    m = Match(id=uuid.uuid4(), tournament_id=uuid.uuid4(), round_number=1, match_number=1, player1_id="P1", player2_id="P2", status=MatchStatus.ACTIVE)

    r1 = MatchReport(id=uuid.uuid4(), match_id=m.id, reporter_id="P1", claimed_winner_id="P1", reported_at=datetime.now())
    r2 = MatchReport(id=uuid.uuid4(), match_id=m.id, reporter_id="P2", claimed_winner_id="P1", reported_at=datetime.now())

    submit_report(m, [], r1)
    assert m.status == MatchStatus.AWAITING_CONFIRMATION
    assert m.winner_id is None

    submit_report(m, [r1], r2)
    assert m.status == MatchStatus.RESOLVED
    assert m.winner_id == "P1"

def test_match_dispute():
    m = Match(id=uuid.uuid4(), tournament_id=uuid.uuid4(), round_number=1, match_number=1, player1_id="P1", player2_id="P2", status=MatchStatus.ACTIVE)

    r1 = MatchReport(id=uuid.uuid4(), match_id=m.id, reporter_id="P1", claimed_winner_id="P1", reported_at=datetime.now())
    r2 = MatchReport(id=uuid.uuid4(), match_id=m.id, reporter_id="P2", claimed_winner_id="P2", reported_at=datetime.now())

    submit_report(m, [], r1)
    submit_report(m, [r1], r2)

    assert m.status == MatchStatus.DISPUTED
    assert m.winner_id is None

def test_invalid_reporter():
    m = Match(id=uuid.uuid4(), tournament_id=uuid.uuid4(), round_number=1, match_number=1, player1_id="P1", player2_id="P2", status=MatchStatus.ACTIVE)
    r1 = MatchReport(id=uuid.uuid4(), match_id=m.id, reporter_id="P99", claimed_winner_id="P1", reported_at=datetime.now())

    with pytest.raises(InvalidStateError, match="not assigned to you"):
        submit_report(m, [], r1)

def test_duplicate_reporter():
    m = Match(id=uuid.uuid4(), tournament_id=uuid.uuid4(), round_number=1, match_number=1, player1_id="P1", player2_id="P2", status=MatchStatus.ACTIVE)
    r1 = MatchReport(id=uuid.uuid4(), match_id=m.id, reporter_id="P1", claimed_winner_id="P1", reported_at=datetime.now())
    r2 = MatchReport(id=uuid.uuid4(), match_id=m.id, reporter_id="P1", claimed_winner_id="P1", reported_at=datetime.now())

    with pytest.raises(InvalidStateError, match="already reported"):
        submit_report(m, [r1], r2)

def test_advance_match_winner():
    m1_id = uuid.uuid4()
    m2_id = uuid.uuid4()

    m1 = Match(id=m1_id, tournament_id=uuid.uuid4(), round_number=1, match_number=1, player1_id="P1", player2_id="P2", status=MatchStatus.RESOLVED, winner_id="P1", next_match_id=m2_id, next_match_slot=1)

    m2 = Match(id=m2_id, tournament_id=m1.tournament_id, round_number=2, match_number=1, player1_id=None, player2_id="P3", status=MatchStatus.PENDING)

    advance_match_winner(m1, m2)

    assert m2.player1_id == "P1"
    assert m2.status == MatchStatus.ACTIVE # Because P3 was already there
