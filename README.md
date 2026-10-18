# Block Breaker offline solver

The original ADB / image recognition prototype is in `main.py`, `block_lib.py`,
`config.py`, and the converted experiment scripts listed below. The new offline path is `solver.py` + `offline.py`.
It uses the existing 41 shape definitions in `config.py` and needs only Python
3.10+ and NumPy. No emulator, ADB server, trained model, or GPU is needed.

## Run

From this directory, using a Python environment with NumPy installed:

```sh
python3 offline.py
python3 offline.py --scenario order-matters
python3 offline.py --random 100 --seed 42
python3 -m unittest discover -s tests -v
```

`--random` adds repeatable synthetic boards to the fixtures. These are stress
inputs, not a claim about the game's distribution or reachable board states.
The runner prints the initial board, piece identities, complete move sequence,
resulting board, heuristic score, search time, and unique search-state count.
Displayed row/column/piece numbers start at 1; Python API values start at 0.

## Boards and pieces

Edit `scenarios.json` or pass another JSON file with `--fixtures path.json`.
Each scenario has a name, eight rows, and one to three shape names:

```json
{
  "name": "cross-clear",
  "board": [".#######", "#.......", "#.......", "#.......",
            "#.......", "#.......", "#.......", "#......."],
  "pieces": ["zz_single", "square_3", "line_5_v"]
}
```

`.` / `0` means empty; `#` / `1` means occupied. Pieces are specified by the
names in `config.shape_classes`. Duplicate pieces are supported and keep their
original tray indices. A move's row/column identifies the top-left of the
piece's bounding rectangle, even when that rectangle's corner cell is empty.

Included fixtures cover an open board, a simultaneous row/column clear, a turn
requiring a different piece order, fragmented space, no legal move, and the old
solver experiment's board. All 41 shapes are exercised by the rules tests.

## Rules and meaning of “best”

Current assumptions, pending verification against the exact game version:

- 8x8 board, fixed piece orientation, no gravity.
- A piece can occupy only empty cells and must remain inside the board.
- After each placement, every completed row and column clears simultaneously.
- The supplied pieces may be used in any order, each at most once.

Search examines every legal sequence for the supplied pieces, with no time or
beam cutoff. It ranks sequences by:

1. Number of pieces successfully placed (always the first priority).
2. Final-board heuristic plus two points per completed line across the sequence.

The initial heuristic is:

```
empty cells + 4 * empty 2x2 windows + 10 * empty 3x3 windows
            - 8 * isolated empty cells
```

Windows overlap. An isolated empty cell has no orthogonally adjacent empty
neighbor. This is an explicit, provisional survival heuristic, **not the game's
score**, nor proof of optimal long-term play. It favors space for large square
pieces, but doesn't yet model future piece probabilities, combo scoring, or
all shape-specific opportunities. Those need empirical tuning using simulated
multi-turn games and then real game observations.

If the whole tray cannot be placed, the solver returns its best partial
sequence. If no move is possible, it returns an empty sequence. Ties are stable:
piece indices and placements are considered in ascending order.

## Correctness and speed

`tests/test_solver.py` contains a separate cell-based reference implementation.
It checks all shape placements on sampled boards, collision/boundary rejection,
simultaneous clears, evaluation features, duplicate pieces, partial/no solutions,
and search results against exhaustive reference searches. It also replays each
fixture's returned moves independently to verify the predicted final board.

Production rules use a 64-bit board, precomputed placement masks, and memoized
search states. Caches are discarded after each search. This structure can later
be ported to Rust or C++ while retaining the Python reference tests and fixtures.
Runtime and memory depend on available moves; reported timings exclude process
startup and first-time placement-mask construction. There is no latency bound.

## Connecting the emulator later

Keep screenshot recognition and input outside the solver. Recognition should
produce a board and tray shape names; input should consume the first returned
move. After dragging, read the board again and compare it with `apply_move`'s
prediction before continuing. Emulator pixel coordinates and drag offsets must
be calibrated separately from logical board coordinates.

The existing `main.py` still calls the old `calc.py` solver. The offline solver
has not yet been connected to live input. No live gameplay is needed for these
tests.


## Former notebooks

All four notebooks have been converted to regular Python scripts. Each has a
`main()` entry point, so importing it does not capture screenshots, train a
model, plot figures, or run examples. Original code cells and commented-out
experiments are retained in order. Saved notebook outputs and embedded plots
are omitted; running the scripts produces fresh output.

| Script | Purpose | Working directory |
| --- | --- | --- |
| `main_experiments.py` | ADB touch experiment, board sampling, contour and hull visualizations | Project root |
| `shape_model/screenshots.py` | Capture piece crops, train/validate the CNN, save the model, run sample predictions, list classes | `shape_model/` |
| `shape_mapping/shape_mapping.py` | Original shape-mapping definitions and printing example | Project root |
| `calculate/calc.py` | Original backtracking example and sample board | Project root |

Run the two offline legacy examples from the project root:

```sh
python3 calculate/calc.py
python3 shape_mapping/shape_mapping.py
```

The vision experiments require the original dependencies: pure-python-adb,
OpenCV, Pillow, Matplotlib, NumPy, and (for training) PyTorch and torchvision.
They also require a connected ADB device for their initial interaction/capture.
`main_experiments.py` sends the original touch gesture and reads the existing
`screen.png`; its screenshot-saving code remains commented out as before.
Matplotlib figures now appear through the configured plotting backend.

To run the complete capture/training experiment with its original relative paths:

```sh
cd shape_model
../.venv/bin/python screenshots.py
```

This runs all former cells sequentially, including 20 training epochs and
writing `shape_model/shape_classifier.pth`. Close plot windows to continue when
using a blocking GUI backend. The original notebook allowed manually running
individual cells; the script runs the whole sequence.

Two existing execution defects were corrected during conversion: the solver
example now passes its three pieces as the list its function expects, and the
training experiment's reloaded inference model uses the same device as its
input tensors. Algorithms, shape definitions, hyperparameters, image crops,
and existing application entry points are otherwise unchanged. The historical
shape-mapping experiment retains its original set-based definitions; the actual
application continues to use the NumPy definitions in `config.py`.
