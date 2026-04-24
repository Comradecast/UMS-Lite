from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid

# Enums mapped to SQLite types

class TournamentState(str, Enum):
    DRAFT = "DRAFT"
    REGISTRATION_OPEN = "REGISTRATION_OPEN"
    REGISTRATION_CLOSED = "REGISTRATION_CLOSED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class MatchStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    DISPUTED = "DISPUTED"
    RESOLVED = "RESOLVED"

# Dataclass models representing Core Entities

@dataclass
class GuildConfig:
    guild_id: str
    admin_role_id: Optional[str] = None
    participant_role_id: Optional[str] = None
    elo_enabled: bool = False
    registration_channel_id: Optional[str] = None
    match_channel_id: Optional[str] = None
    results_channel_id: Optional[str] = None

@dataclass
class PlayerProfile:
    discord_id: str
    global_ums_id: Optional[uuid.UUID] = None
    username: Optional[str] = None
    wins: int = 0
    losses: int = 0
    matches_played: int = 0
    tournaments_played: int = 0

@dataclass
class Tournament:
    id: uuid.UUID
    guild_id: str
    name: str
    state: TournamentState
    created_at: datetime
    panel_channel_id: Optional[str] = None
    panel_message_id: Optional[str] = None
    scheduled_start_time: Optional[str] = None
    region: Optional[str] = None
    format: str = "1v1"

@dataclass
class TournamentEntry:
    id: uuid.UUID
    tournament_id: uuid.UUID
    player_id: str
    joined_at: datetime

@dataclass
class Match:
    id: uuid.UUID
    tournament_id: uuid.UUID
    round_number: int
    match_number: int
    player1_id: Optional[str] = None
    player2_id: Optional[str] = None
    winner_id: Optional[str] = None
    status: MatchStatus = MatchStatus.PENDING
    next_match_id: Optional[uuid.UUID] = None
    next_match_slot: Optional[int] = None
    message_channel_id: Optional[str] = None
    message_id: Optional[str] = None

@dataclass
class MatchReport:
    id: uuid.UUID
    match_id: uuid.UUID
    reporter_id: str
    claimed_winner_id: str
    reported_at: datetime

@dataclass
class AdminActionLog:
    id: uuid.UUID
    guild_id: str
    admin_id: str
    action_type: str
    target_entity_id: Optional[uuid.UUID]
    details: str # We can serialize JSON here for sqlite
    timestamp: datetime
