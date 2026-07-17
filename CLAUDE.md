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
- **Run the graphical real-time game:** `pip install -r requirements.txt` then
  `python play.py` (opencv window; left-click a piece then a target to move,
  right-click to jump, ESC/q to quit).
- **Tests:** `pytest` (201 tests). Single file: `pytest tests/test_engine.py`.
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
  validated motions on the arbiter, advances time, records moves
  (`move_log.py`), scores captures (`scoreboard.py`, `notation.py`), and exposes
  read models. `controller.py` owns selection state and turns pixel clicks into
  engine commands (via `board_mapper.py`); `parser.py` splits a script into
  board/commands sections. `composition.py` is the **single composition root** —
  the one place the whole dependency graph is wired.
- `view/` — read-only view models. `snapshot.py` (`GameSnapshot`) + `renderer.py`
  produce the canonical text render; `render_model.py` (`RenderModel`) is the
  rich read model for the GUI. The view never touches the live board.
- `graphics/` — cv2 adapters (`Img` drawing primitive, `Window`) and sprite
  loading (`assets.py`, `sprite*.py`).
- `ui/` — `game_loop.py` (real-time frame loop), `graphics_renderer.py`
  (`RenderModel` → canvas), `hud.py`, `input_source.py`, `move_table_panel.py`.
  Only `graphics/`, `ui/`, and `play.py` read the GUI-only config; the text/VPL
  path never touches them, so the grader is unaffected.
- `gateway/` — `GameGateway` Protocol + `NetworkGateway` stub for a future
  networked mode. `RenderModel` is deliberately the serializable read model a
  server would send and a client would draw.

**Two entry points, one graph:** `main.py` (`run`) drives the text script and
must stay grader-stable; `play.py` builds the *same* `GameEngine` from
`assets/board.csv` for the real-time loop. Both defer only board loading to
themselves and delegate the rest of the wiring to `game/composition.py`.

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
