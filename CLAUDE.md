# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

KungFu Chess: a real-time ("kung fu") chess variant where moves and jumps
resolve after a delay instead of instantly, both colors act at any time (no
turns), and a jump onto a square can intercept an incoming enemy move. It is a
bootcamp assignment graded iteration-by-iteration by VPL (Virtual Programming
Lab) via exact stdout matching, so the text entry point's output format is
load-bearing. See `README.md` for the domain narrative and the four grading
requirements.

## Commands

- **Run the text command-script (what VPL grades):** `python main.py < script.txt`
  — reads a `Board:` / `Commands:` script from stdin, executes `click x y`,
  `jump x y`, `wait ms`, `print board`, and prints the canonical board.
- **Run the graphical real-time game (local):** `pip install -r requirements.txt`
  then `python play.py` (opencv window; left-click a piece then a target to move,
  double-click to jump, ESC/q to quit).
- **Run it over a network:** `python -m server` starts the authoritative game on
  a websocket; `python -m client` opens a window that plays against it. Several
  clients share one server and see the same game.
- **Tests:** `pytest` (368 tests). Single file: `pytest tests/test_engine.py`.
  Single test: `pytest tests/test_engine.py::test_name` or `pytest -k name`.
- **Coverage:** `pytest --cov` (config in `.coveragerc`; `htmlcov/` is
  intentionally committed as a browsable report). Product code is measured at
  100%; `tests/`, `conftest.py`, and the vendored `graphics/img.py` are omitted,
  and GUI shells use `# pragma: no cover`.

`conftest.py` puts the repo root on `sys.path`, so all imports are top-level
package imports (`from game.engine import GameEngine`), run from the repo root.

## Architecture

The design goal is that each real responsibility lives in its own layer so it is
testable in isolation and a new rule/feature extends one layer without touching
the others. `GameEngine` is a **thin coordinator** that owns none of the details
it sequences.

**Layers (dependencies point downward; the engine wires them):**

- `board/` — `Board` is the single internal representation (logical occupancy
  only, private list-of-lists behind a public interface). `loaders.py` holds
  input-format *adapters* (`load_text_board`, `load_csv_board`) — new input
  formats are added here, never by subclassing `Board`.
- `rules/` — pure legality, no time, no mutation. `movement_strategy.py` +
  `piece_rules.py` are per-kind `MovementStrategy` objects registered by letter
  in `rule_registry.py` (Strategy + Registry). `rule_engine.py` (`RuleEngine`)
  does read-only validation returning a stable `Reason` code and computes
  `legal_targets` for move hints. `game_conditions.py` holds pluggable
  `WinCondition` / promotion strategies.
- `realtime/` — `RealTimeArbiter` owns ALL motion over simulated time: active
  `Move`/`Jump` objects, the clock, per-cell step timing, arrivals, capture,
  interception, and cooldowns. It is a **pure stepping mechanism**: it walks a
  precomputed `path` handed in by the rules layer one cell per step and obeys a
  single `may_capture_final` flag; it never imports or queries the rules layer.
  Time only advances when `advance_time(dt)` is called (never wall-clock). It
  reports `ArrivalEvent`s back up; it does not decide the win condition.
- `game/` — `GameEngine` (`engine.py`) is the public command boundary: it
  applies application-level guards (game over, busy/resting, the
  `ALLOW_CONCURRENT_MOVES` policy), delegates validation to `RuleEngine`, starts
  validated motions on the arbiter, advances time, and **publishes** what
  happened on the `EventBus` (see `events/`), never calling its consumers by
  name. `controller.py` owns selection state and turns pixel clicks into gateway
  commands (via `board_mapper.py`), deciding what a click does from the render
  model rather than a command's reply, so it drives a remote game unchanged;
  `subscribers.py` (`MoveRecorder`, `CaptureScorer`) writes the move log and
  score off the bus; `squares.py` is the one place a file/rank square (`e2`) is
  written and read; `parser.py` splits a script into board/commands sections.
  `composition.py` is the **single composition root** — the one place the whole
  dependency graph is wired.
- `events/` — `EventBus`: a domain-agnostic publish/subscribe mechanism that
  routes each event to the subscribers of its exact type. `game/events.py` holds
  the vocabulary (`GameStarted`, `MoveCompleted`, `PieceCaptured`, `JumpStarted`,
  `GameEnded`); a subscriber is any callable, so nothing inherits an interface.
  This is what lets a new consumer — a sound, a banner, a network broadcaster —
  attach without the engine changing.
- `view/` — read-only view models. `snapshot.py` (`GameSnapshot`) + `renderer.py`
  produce the canonical text render; `render_model.py` (`RenderModel`) is the
  rich read model for the GUI. The view never touches the live board.
- `graphics/` — cv2 adapters (`Img` drawing primitive, `Window`) and sprite
  loading (`assets.py`, `sprite*.py`).
- `ui/` — `game_loop.py` (real-time frame loop), `graphics_renderer.py`
  (`RenderModel` → canvas), `hud.py`, `animation.py` (banner), `input_source.py`,
  `move_table_panel.py`, and `composition.py` — the **one place the graphical UI
  is wired**, shared by the local and networked entry points, which differ only
  in which gateway they hand it. Only `graphics/`, `ui/`, `audio/`, and the GUI
  entry points read the GUI-only config; the text/VPL path never touches them.
- `audio/` — sound as presentation, kept out of `game/`: `player.py` wraps
  winsound, `cues.py` subscribes one sound per event to the bus.
- `gateway/` — the `GameGateway` Protocol the UI depends on, never the concrete
  engine. `GameEngine` satisfies it in-process; `client/NetworkGateway` satisfies
  it over the wire. Commands report nothing back (a remote reply could not arrive
  in time); everything the UI learns comes from the `RenderModel`.
- `protocol/` — pure translation to and from what crosses the wire, with no I/O:
  `commands.py` (`WQe2e5`), `state.py` (`RenderModel`), `events.py` (bus events),
  `messages.py` (the JSON envelope), over the shared `records.py` mechanism.
  Tested in full without a socket, exactly as `board/loaders.py` is.
- `server/` — what turns the game into a service. `broadcast.py` relays events
  and state; `handler.py` turns client messages into engine commands, trusting
  only the squares (never the piece a client claims); `service.py` is the game a
  socket drives; `socket.py` is the sole websockets/asyncio shell; `outbox.py`
  queues lines so the blocking game never awaits the network. `python -m server`
  wires it, and is the **only place the clock advances**.
- `client/` — a window with no game inside it. `gateway.py` is the remote proxy;
  `inbox.py` is the single point the two threads meet (socket thread writes,
  frame loop reads); `router.py` places each arriving message (state and hints
  to the inbox, events republished on the client's own bus); `socket.py` is the
  websockets shell, on a background thread because the cv2 loop blocks;
  `waiting.py` is the screen shown until the first state arrives.

**Four entry points, one graph:** `main.py` (text script, grader-stable),
`play.py` (local GUI), `python -m server` (authoritative networked game), and
`python -m client` (a window that draws it). All build the *same* `GameEngine`
via `game/composition.py`, differing only in where the board comes from and, for
the client, in swapping the engine for a `NetworkGateway` behind the same
`GameGateway` contract.

## Conventions that constrain how you write code

- **VPL grader runs Python < 3.10.** Every module starts with
  `from __future__ import annotations`, and runtime `X | None` forms are avoided
  (only in annotations, which the future-import defers). Do not rely on
  match-statements or other 3.10+ syntax in product code. (Local dev is 3.13.)
- **No monkeypatching in tests — dependency injection instead.** `GameEngine`,
  `RuleEngine`, the arbiter, and `main.run` take every collaborator (board,
  registry, win condition, promotion rule, `config`) as a constructor/function
  argument, so tests substitute fakes. `config=settings` is injectable
  everywhere rather than importing the module directly. The one accepted
  exception is `main(input_stream=...)` at the outermost stdin boundary.
- **No magic numbers or hardcoded strings.** All constants (timing, colors,
  pawn direction, empty-cell token, piece values, window layout) live in
  `config/settings.py`. Piece kinds and win conditions are registered
  strategies, not hardcoded branches. The pawn double-step home rank is *derived
  from board height*, not stored, so rules hold on any board size — see the
  README's "Pawn double-step" note before touching `PawnMovement`.
- **Branch/commit workflow:** typed branches (`feature/*`, `fix/*`). Propose the
  exact git commands and a commit message for the user to run rather than
  committing autonomously; do not add a `Co-Authored-By` trailer. `slice_sprites.py`
  and `remove_background.py` are gitignored local sprite-prep tooling, not part
  of the project.
