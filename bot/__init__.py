"""The computer opponent: a player the server seats in a room itself.

Three layers, each knowing only the one below it:

- `player.ComputerPlayer` - lives in a room and is ticked with it, on the game
  loop. It snapshots the board into a `position.Position`, hands the snapshot
  to a strategy on a worker thread, and plays the answer back on the loop. The
  live engine is only ever touched from the loop thread, so nothing is locked.
- `strategy` - turns a Position into a move. `GreedyStrategy` takes the most
  valuable piece in reach; `FallbackStrategy` asks one strategy and falls back
  to another when it fails.
- `gemini.GeminiStrategy` - asks Gemini, through a single `make_move` tool,
  under one rate limit shared by every room on the server.

`factory` wires them from config: Gemini first, greedy behind it, or greedy
alone when there is no key.
"""
