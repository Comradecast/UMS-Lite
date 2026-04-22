# UMS Lite: Product Definition and Architecture Baseline

## 1. Product Statement

**What it is:**
UMS (Unified Match System) Lite is a lightweight, standalone, single-server Discord bot designed to manage 1v1 Rocket League Sideswipe tournaments. It provides a polished, intuitive, button-heavy user experience for both players and tournament administrators. UMS Lite handles the entire lifecycle of a localized tournament—from registration and bracketing to match reporting and dispute resolution—acting as a robust, isolated node that can eventually integrate into a broader multi-server federated ecosystem.

**What it is not:**
UMS Lite is not a cross-server federated application. It does not handle player Elo ratings, global leaderboards, seasonal circuits, team-based (2v2+) events, or double-elimination formats. It is strictly focused on executing isolated, single-elimination 1v1 tournaments flawlessly within a single Discord server.

---

## 2. MVP Scope

**In-Scope:**
- Single-server deployment and operation via Python and `discord.py`.
- Localized SQLite database for persistence.
- 1v1 tournament creation and management.
- Single-elimination bracket generation (randomized seeding).
- Bomb-proof, button-heavy Discord UX (Slash commands for setup, buttons/modals for interaction).
- Automated match progression based on dual-confirmation score reporting.
- Admin dispute resolution tooling.
- Automatic temporary role assignment for tournament participants.
- Admin action auditing and logging.

**Out-of-Scope:**
- Multi-server/federated data sharing.
- 2v2 or team-based tournament structures.
- Double-elimination, Swiss, or Round Robin formats.
- Global player rankings, Elo, or MMR tracking.
- Web dashboards or external APIs.
- Complex seeding algorithms (manual or rank-based).
- Match check-in timers or automated disqualifications (handled manually by admins for the MVP).

---

## 3. User Roles

**Admin / Tournament Organizer:**
- Must possess a specific designated Discord role (e.g., "UMS Admin") or have the standard Discord `Manage Server` permission.
- **Capabilities:** Create tournaments, open/close registration, generate brackets, force-start matches, manually adjust scores, resolve disputes, finalize or cancel tournaments, and view audit logs.

**Player:**
- Any standard Discord user in the server.
- **Capabilities:** View active tournaments, join/leave open tournaments, view the current bracket, report match scores via buttons, and confirm/dispute opponent-reported scores.

*(Note: For UMS Lite, Admin and Organizer/Moderator are treated as a single unified role to reduce complexity.)*

---

## 4. Tournament Lifecycle

**Tournament States:**
1. `DRAFT`: Created but not yet visible for registration.
2. `REGISTRATION_OPEN`: Players can join and leave.
3. `REGISTRATION_CLOSED`: No more joins/leaves; bracket generation is possible.
4. `IN_PROGRESS`: Bracket generated; matches are active and scoring is enabled.
5. `COMPLETED`: Tournament finished; winner declared.
6. `CANCELLED`: Tournament forcefully terminated by an admin.

**State Transitions & Triggers:**
- `DRAFT` -> `REGISTRATION_OPEN`: Admin triggers "Open Registration".
- `REGISTRATION_OPEN` -> `REGISTRATION_CLOSED`: Admin triggers "Close Registration".
- `REGISTRATION_CLOSED` -> `IN_PROGRESS`: Admin triggers "Generate Bracket & Start". (Fails if < 2 players).
- `IN_PROGRESS` -> `COMPLETED`: System automatically transitions when the final match is resolved.
- `[ANY STATE]` -> `CANCELLED`: Admin triggers "Cancel Tournament".

---

## 5. Core Entities

These entities map directly to the SQLite schema. To future-proof for federation, Discord IDs are stored as strings, and UUIDs are used for internal primary keys.

- **GuildConfig**
  - `guild_id` (String, PK)
  - `admin_role_id` (String, nullable)
  - `participant_role_id` (String, nullable)

- **PlayerProfile**
  - `discord_id` (String, PK)
  - `global_ums_id` (UUID, nullable - reserved for future federation)
  - `username` (String, cached display name)

- **Tournament**
  - `id` (UUID, PK)
  - `guild_id` (String, FK)
  - `name` (String)
  - `state` (Enum: DRAFT, REGISTRATION_OPEN, REGISTRATION_CLOSED, IN_PROGRESS, COMPLETED, CANCELLED)
  - `created_at` (Timestamp)

- **TournamentEntry**
  - `id` (UUID, PK)
  - `tournament_id` (UUID, FK)
  - `player_id` (String, FK -> PlayerProfile.discord_id)
  - `joined_at` (Timestamp)

- **Match**
  - `id` (UUID, PK)
  - `tournament_id` (UUID, FK)
  - `round_number` (Integer)
  - `match_number` (Integer)
  - `player1_id` (String, FK, nullable if TBD/Bye)
  - `player2_id` (String, FK, nullable if TBD/Bye)
  - `winner_id` (String, FK, nullable)
  - `status` (Enum: PENDING, ACTIVE, REPORTED, DISPUTED, RESOLVED)
  - `next_match_id` (UUID, FK, nullable - defines the bracket graph)

- **MatchReport**
  - `id` (UUID, PK)
  - `match_id` (UUID, FK)
  - `reporter_id` (String, FK)
  - `claimed_winner_id` (String, FK)
  - `reported_at` (Timestamp)

- **AdminActionLog**
  - `id` (UUID, PK)
  - `guild_id` (String, FK)
  - `admin_id` (String, FK)
  - `action_type` (String - e.g., "FORCE_WIN", "CANCEL_TOURNAMENT")
  - `target_entity_id` (UUID, nullable)
  - `details` (JSON/String)
  - `timestamp` (Timestamp)

---

## 6. UX Surfaces

**Admin Surfaces:**
- `/ums create <name>`: Slash command. Spawns an ephemeral Admin Control Panel (Embed + Buttons).
- **Admin Control Panel:** A persistent-feeling interface (re-sent or updated dynamically) containing buttons: [Open Registration], [Close Registration], [Generate Bracket], [Cancel Tournament].
- **Dispute Resolution Panel:** Triggered via DM or Admin Channel when a match is disputed. Contains details of the reports and buttons: [Force Win P1], [Force Win P2], [Reset Match].

**Player Surfaces:**
- **Tournament Announcement Panel:** A public channel embed posted when registration opens. Contains:
  - Tournament details, status, and current entrant count.
  - Button: [Join Tournament] / [Leave Tournament] (Toggles based on state).
- **Match Card Panel:** Sent to a dedicated match channel or thread (or DM) when a match becomes ACTIVE.
  - Pings both players.
  - Embed detailing the match (Player 1 vs Player 2).
  - Buttons: [I Won], [I Lost].
- **Bracket View:** Accessible via `/ums bracket` (returns a text-based ASCII bracket or an image if rendered) or a persistent read-only message updated dynamically.

---

## 7. Admin Workflows

1. **Create Tournament:** Admin uses `/ums create "Weekly Cup"`. Bot creates DB record (DRAFT) and shows the Admin Control Panel.
2. **Open Registration:** Admin clicks [Open Registration]. Bot updates state, posts the public Announcement Panel with the [Join] button.
3. **Close Registration:** Admin clicks [Close Registration]. Join buttons are disabled.
4. **Generate Bracket & Start:** Admin clicks [Generate Bracket]. Bot shuffles entries, creates `Match` records linking `next_match_id`s, transitions state to IN_PROGRESS, and posts Match Cards for Round 1.
5. **Resolve Disputes:** If players report conflicting results, state becomes DISPUTED. Admin is notified, reviews the Match, and clicks [Force Win P1] on the Dispute Panel. The bot advances P1 and logs the action.
6. **Finalize Tournament:** Automated when the final match concludes. Admin can review.
7. **Cancel Tournament:** Admin clicks [Cancel Tournament] in the control panel. All active matches are voided, roles are stripped, and the tournament is archived.

---

## 8. Player Workflows

1. **Join Tournament:** Player clicks [Join] on the Announcement Panel. The bot registers them, assigns the participant role, and updates the entrant count on the embed.
2. **View Bracket/Status:** Player uses `/ums status` or checks the pinned Bracket message to see upcoming opponents.
3. **Report Match Result:** When their match is active, Player A clicks [I Won]. The bot waits for Player B.
4. **Confirm/Dispute:** Player B clicks [I Lost] -> Match resolves, Player A advances. If Player B clicks [I Won], the match enters the DISPUTED state, pausing advancement and notifying admins.

---

## 9. Architecture Baseline

The bot will strictly separate Discord I/O from core business logic to ensure testability and future-proofing.

**Directory Structure:**
```
ums_lite/
├── bot.py             # Entry point, discord.py bot initialization
├── config.py          # Environment variables, constants
├── core/              # Pure Python domain logic (No discord.py dependencies)
│   ├── bracket.py     # Bracket generation algorithms
│   ├── tournament.py  # State machine and transition logic
│   └── match.py       # Scoring and resolution rules
├── db/                # Persistence layer
│   ├── database.py    # SQLite connection and setup
│   ├── models.py      # Dataclasses/Pydantic models mapping to Core Entities
│   └── repositories.py # CRUD operations (e.g., TournamentRepo, MatchRepo)
├── cogs/              # Discord UI Layer (discord.py Cogs)
│   ├── admin.py       # Admin slash commands
│   ├── player.py      # Player commands
│   └── events.py      # General error handling and connection events
└── ui/                # discord.py Views and Modals
    ├── panels.py      # Admin Control Panel, Announcement Panel
    └── match_views.py # Match reporting button views
```

**Coupling Rule:** `core/` modules must accept pure data structures (IDs, enums) and return data structures or throw specific Domain Exceptions. They must never accept `discord.Interaction` or `discord.Member` objects. `cogs/` and `ui/` are responsible for translating Discord interactions into domain calls and rendering the results.

---

## 10. Governance Rules

- **Fail-Closed Behaviors:** If a database transaction fails during a state transition (e.g., bracket generation), the state is rolled back. The bot will respond to the Discord interaction with a generic error and log the stack trace.
- **Deterministic Advancement:** Matches only advance if: (A) Player 1 reports WIN and Player 2 reports LOSS. (B) Player 1 reports LOSS and Player 2 reports WIN. (C) An Admin executes a Force Win.
- **Dispute Handling:** Any combination of double-WIN, double-LOSS, or conflicting reports immediately halts the match progression, tags it as DISPUTED, and requires Admin intervention. Players cannot change their vote once cast.
- **Auditability:** Every state transition forced by an admin (Force Win, Cancel, Manual Bracket Edit) must write an immutable record to `AdminActionLog` with the admin's Discord ID and the exact action payload.

---

## 11. Phase Plan

**Phase 1: Foundation & Persistence**
- Setup project structure, SQLite database, and repository layer.
- Implement the core Entity models.
- Write unit tests for basic CRUD operations.

**Phase 2: Core Domain Logic**
- Implement the tournament state machine (`core/tournament.py`).
- Implement the single-elimination bracket generation algorithm with bye-handling (`core/bracket.py`).
- Write comprehensive unit tests for bracket generation and match advancement rules.

**Phase 3: Discord UX - Setup & Registration**
- Implement `cogs/admin.py` and `ui/panels.py`.
- Build the `/ums create` flow, Admin Control Panel, and Tournament Announcement Panel.
- Enable players to click [Join] and update the database and UI embed.

**Phase 4: Discord UX - Match Execution**
- Implement the transition to IN_PROGRESS.
- Build the Match Card Panel with [I Won] / [I Lost] buttons.
- Wire the button interactions to the core match advancement logic.

**Phase 5: Governance & Polish**
- Implement Admin Dispute Resolution flows.
- Implement automated role management.
- Finalize error handling, audit logging, and documentation.
