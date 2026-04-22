import math
import uuid
from typing import List, Tuple, Optional

from ums_lite.db.models import Match, MatchStatus

def generate_bracket(tournament_id: uuid.UUID, ordered_players: List[str]) -> List[Match]:
    """
    Generates a single-elimination bracket for the given list of player IDs.
    Returns a list of Match entities.
    Expects ordered_players to be deterministically ordered (seeded) before calling.
    Players placed against a Bye will have a None opponent in Round 1 and auto-advance.
    """
    num_players = len(ordered_players)
    if num_players < 2:
        raise ValueError("Cannot generate bracket with fewer than 2 players.")

    # Calculate bracket size (next power of 2)
    num_rounds = math.ceil(math.log2(num_players))
    bracket_size = 2 ** num_rounds

    # Calculate number of byes
    num_byes = bracket_size - num_players

    # Standard deterministic seeding pattern logic for single elimination.
    # We create a placeholder list of size `bracket_size` with ordered_players at the front,
    # and fill the rest with None to represent Byes.
    # However, proper seeding means we distribute byes to the top seeds.
    # For a simple deterministic implementation without complex standard seeding trees,
    # we pair: seed 1 vs bye, seed 2 vs bye... up to num_byes.

    # Seed array: indices 0 to bracket_size-1. None means Bye.
    seeded_slots: List[Optional[str]] = [None] * bracket_size

    # Distribute standard seeded match ups if we had a full tree:
    # A simple but deterministic approach for UMS Lite:
    # The first `num_byes` players get a Bye. The remaining players play each other.
    # So top `num_byes` seeds go straight to Round 2.
    # To represent this in Round 1 matches, we pair them with None.

    # Fill round 1 matchups:
    # matches will be pairs of (player1, player2) where player2 might be None (Bye)
    round_1_matchups: List[Tuple[Optional[str], Optional[str]]] = []

    player_idx = 0

    # Top seeds get byes
    for i in range(num_byes):
        round_1_matchups.append((ordered_players[player_idx], None))
        player_idx += 1

    # The rest play each other
    while player_idx < num_players:
        p1 = ordered_players[player_idx]
        player_idx += 1
        p2 = ordered_players[player_idx] if player_idx < num_players else None
        round_1_matchups.append((p1, p2))
        if p2 is not None:
            player_idx += 1

    # We now have the Round 1 matchups.
    # Now we need to build the tree from the Finals backward, or Round 1 forward.
    # Building forward:
    matches: List[Match] = []

    # To link matches, we'll keep track of matches created per round
    # round_matches[round_number] = [Match, Match, ...]
    round_matches: dict[int, List[Match]] = {}

    # Create Round 1 matches
    round_1 = []
    match_counter = 1
    for p1, p2 in round_1_matchups:
        # If it's a bye match, it resolves immediately and winner is p1
        status = MatchStatus.RESOLVED if p2 is None else MatchStatus.PENDING
        winner = p1 if p2 is None else None

        m = Match(
            id=uuid.uuid4(),
            tournament_id=tournament_id,
            round_number=1,
            match_number=match_counter,
            player1_id=p1,
            player2_id=p2,
            winner_id=winner,
            status=status
        )
        round_1.append(m)
        matches.append(m)
        match_counter += 1

    round_matches[1] = round_1

    # Generate subsequent rounds
    current_round = 1
    while current_round < num_rounds:
        prev_round_matches = round_matches[current_round]
        next_round = []
        next_round_num = current_round + 1

        # Every 2 matches in previous round feed into 1 match in next round
        for i in range(0, len(prev_round_matches), 2):
            m1 = prev_round_matches[i]
            # There might not be an m2 if we just had 1 match feeding into a final (shouldn't happen with power of 2 tree structure but handle safely)
            m2 = prev_round_matches[i+1] if i+1 < len(prev_round_matches) else None

            # Create next round match
            next_m = Match(
                id=uuid.uuid4(),
                tournament_id=tournament_id,
                round_number=next_round_num,
                match_number=match_counter,
                status=MatchStatus.PENDING
            )

            # If both feeding matches were byes (resolved), this match becomes active (or resolved if it's two byes, which shouldn't happen)
            if m1.status == MatchStatus.RESOLVED and m2 and m2.status == MatchStatus.RESOLVED:
                next_m.player1_id = m1.winner_id
                next_m.player2_id = m2.winner_id
                next_m.status = MatchStatus.ACTIVE # Ready to play
            elif m1.status == MatchStatus.RESOLVED:
                next_m.player1_id = m1.winner_id
            elif m2 and m2.status == MatchStatus.RESOLVED:
                next_m.player2_id = m2.winner_id

            next_round.append(next_m)
            matches.append(next_m)
            match_counter += 1

            # Link previous round matches to this match
            m1.next_match_id = next_m.id
            m1.next_match_slot = 1

            if m2:
                m2.next_match_id = next_m.id
                m2.next_match_slot = 2

        round_matches[next_round_num] = next_round
        current_round += 1

    # Set all round 1 matches that don't have byes to ACTIVE so they can be played
    for m in round_matches[1]:
        if m.status == MatchStatus.PENDING:
            m.status = MatchStatus.ACTIVE

    # For any advanced matches that got populated with two players due to byes, ensure they are ACTIVE
    for m in matches:
        if m.status == MatchStatus.PENDING and m.player1_id is not None and m.player2_id is not None:
            m.status = MatchStatus.ACTIVE

    return matches
