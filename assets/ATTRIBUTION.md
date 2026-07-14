# Asset attribution

The board background (`board.png`), piece sprites (`pieces/`) and the starting
position format are vendored from the course asset pack:

- **KamaTechOrg / CTD26** — https://github.com/KamaTechOrg/CTD26 (`pieces1/`, `board.png`)

`board.csv` here is a standard chess starting position, authored for this
project in the same CTD26 cell-code format (`KIND+COLOR`, e.g. `PW`, `KB`).

The piece sprites are development placeholders (each frame is labelled with its
state, e.g. "idle 1"); the animation state machine treats them purely as data.
