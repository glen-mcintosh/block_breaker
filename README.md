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

## Block Blast on Waydroid

The current screen profile is calibrated for the **450 x 1000 portrait layout**
with adaptive recognition across color themes. `live.py` reads a screen and sends its board and pieces to
the new offline solver. It sends touch input only with `--play`. The original `main.py`
remains the old model-based entry point; use `live.py` for this Waydroid setup.

```sh
python -m pip install -r requirements-live.txt
adb connect 192.168.240.112:5555
python live.py
```

Use the address shown by `waydroid status` if the IP changes, and accept Android's
ADB debugging authorization prompt if shown. With multiple devices, pass
`--serial 192.168.240.112:5555`.

To analyze an existing screenshot without connecting:

```sh
python live.py --image captures/latest.png
```

The reader uses `screen_profile.json` for resolution, board/tray bounds, and
`recognition: "adaptive"` (the default). Empty board cells have flat interiors;
occupied cells have light/dark bevels at calibrated edge locations. The reader
uses that structure instead of absolute RGB colors. It estimates each tray
slot's background from its side margins, groups the dominant foreground color,
and matches the resulting block grid to the existing 41 shape definitions.
Dragging uses the same detected geometry. A new theme requires no new color
palette or fixed-theme reset, provided this layout and block style are retained.
The old RGB profiles remain available for diagnosis but are unused in adaptive
mode. No trained model, PyTorch, or OpenCV is needed for this path.

`captures/latest.png` is the original capture; `captures/annotated.png` marks
occupied cells cyan, empty cells green, and the first suggested move in yellow.
Tray labels identify the detected shapes. Captures are ignored by Git. Reported
move coordinates are one-based bounding-box origins, not touch coordinates.

Keep the game on a settled gameplay screen. Adaptive recognition has been
checked against saved pink, blue, and gray gameplay screens, plus all 41 shapes
in six generated color schemes (including monochrome). This does not guarantee
every possible game appearance. It still needs contrast between the piece and
tray background and the same beveled block style. Major layout/artwork changes,
low contrast, overlays, and animations can require changes or cause a stop.
Different resolutions still need calibration. `--play` continues to require two
matching predicted board/tray observations before the next move.

`tests/fixtures/screen_expectations.json` records expected board/tray readings
for immutable local gameplay captures. Regression tests use these when the
ignored screenshots are present; on another checkout the synthetic tests still
run, and the archive test skips if no local captures exist. Tests also compare
new drag coordinates against the successful historical move logs.


## Play and capture locations

Current captures use the existing `captures/` and training-data trees:

| Location | Purpose |
| --- | --- |
| `shape_model/shapes/<shape_name>/` | Original training examples plus new outcome-verified crops when `--collect-verified` is enabled |
| `captures/failed_shapes/` | Failed/unrecognized piece crops for manual review, with null labels and failure context |
| `captures/session-*/` | Full before/after screens, stopped screens, and move/error logs |
| `captures/latest.png`, `captures/annotated.png` | Current preview |
| `captures/unclassified/` | Preserved old unlabeled collection and optional manual `--watch` collection |

Normal play no longer duplicates every tray into an unclassified folder. It
always keeps full-screen session evidence and automatically collects failure
crops. For an unverified drag it preserves the selected **pre-drag** crop as
well as relevant visible crops from the stopped screen. A tray error that names
a slot limits the stopped-screen crop to that slot; otherwise visible pieces
are retained as failure context. Recognized empty slots and blank/unavailable
screens do not add images to the piece-review queue. Predictions in JSON are
hints only; failed crops are never automatically labelled or added to training.

Run a bounded play session:

```sh
python -u live.py --play --moves 100
```

Play mode checks two matching observations, solves the remaining pieces, and
rechecks the state before dragging. Each drag uses the measured 110-pixel lift
and 1.5 motion gain at 450x1000. After release, both the expected board and tray
transition must match twice. The next move is solved from the observed state.
It stops on an unexpected result, no legal move, an unreadable screen, or the
move limit. A proven unchanged result can use the bounded retry described below;
it does not dismiss ads/game-over screens.
Stop with Ctrl+C. An intentional interruption is logged but does not classify
pieces as failures.

To collect unlabeled examples while you play manually, explicitly use:

```sh
python live.py --watch
```

Watch mode saves settled changed states to `captures/unclassified/` and puts
unreadable pieces in `captures/failed_shapes/`. Analysis of a saved image writes
previews only on success; a recognition error preserves relevant failed crops.

Custom locations are available via `--dataset` (watch collection),
`--failed-dataset` (failure review), and `--verified-dataset` (verified training).
All default image locations are ignored by Git. Existing original training/test
images and legacy `shapes_dataset/` assets are preserved for the historical
experiments, which still use their original paths.

The old root `unclassified/` collection was moved under `captures/`. Failure
examples recovered from stopped runs were separated into `failed_shapes/`;
matching duplicate PNGs were consolidated while retaining their earlier
metadata. `captures/collection-cleanup.json` records this cleanup. Any old
`verified_shapes/` collection is merged into the existing training class folders.

## Diagnosing pattern-recognition stops

The reader tolerates small shifts in block-interior centers (up to 3.5 pixels
from the expected 22.25-pixel spacing). Bevels and RGB565 dithering can make the
visible interior of the same piece slightly different sizes. If the ordinary
color mask cannot form a valid catalog shape, it tries up to five dominant
color clusters with neighboring shades merged. This prevents a single neutral
shadow shade from outvoting a cyan/light tile whose interior spans several
nearby shades. Fallbacks must still pass block-size, spacing, cell-coverage,
unexplained-pixel, and catalog-shape checks. Successful ordinary masks retain
their original pickup coordinates.

Regression fixtures include the observed light L and cyan single-block stops,
as well as synthetic jitter/shadow cases. A blank/unavailable display raises a
specific error; it is not an empty game board. Wake Waydroid or reopen the game
before restarting a run. This check does not change any screen-timeout setting.

New play failures store `failure.json` beside `stopped.png`, including the error
message and last move. Tray errors identify the affected slot. The player still
stops on an unexpected board/tray rather than guessing or retrying a drag.

To replay every available verified before/after screen against its logged state
without connecting to Waydroid:

```sh
python -u audit_gameplay.py
```

The report is saved as `captures/audit-report.json`; a nonzero exit status means
at least one screenshot was unreadable or disagreed with its logged state.
The audit is a regression check against the existing logs, not independent
proof that every historical interpretation was correct. Stopped screens are
covered by the explicit regression fixtures and tests instead.


## Collect outcome-verified training data

Neither original CNN checkpoint is changed or retrained. The live bot uses
geometric recognition, so collecting data is optional preparation for a future
model. The old 97.28% random-split validation result is not an emulator accuracy
measurement. A future model should use a separately reviewed session holdout
and a new checkpoint filename.

Enable verified collection during play:

```sh
python -u live.py --play --moves 100 --collect-verified
```

Only the selected piece's original **pre-drag tray crop** is labelled, after
actual post-move board and tray readings match the simulated result twice.
The collector re-reads both images and validates the transition, then writes:

```
shape_model/shapes/<shape_name>/<content_hash>.png
shape_model/shapes/<shape_name>/<content_hash>.json
```

Existing training images stay intact. Other tray pieces are not labelled until
they are played and verified. Failed moves go to the separate review queue.
Exact duplicate crops within the class are skipped. Collection remains off
unless `--collect-verified` is supplied; the flag requires `--play`.

JSON records the class, `label_source: "verified_move"`, session, step, crop
bounds, trays, move, expected/observed board, and line clears. These labels are
supported by game outcomes, not independent human review. Spot-check them and
keep a manually reviewed test set out of training. Review failed PNGs later and
move accepted examples into the appropriate training class folder manually.

Use `--verified-dataset /path/to/dataset` to override the existing training root.
There is no automatic model training/replacement. A future trainer should retain
the explicit 41-class mapping, split near-duplicate examples by session, and
save something like `models/shape_classifier_v2.pth`. The historical training
experiment still uses its original checkpoint filename; it is not a versioned
trainer.


## Held-piece checks and bounded drag retries

Every play gesture now pauses with the piece held over its target. It saves
`<step>-attempt-<n>-held.png` and a matching JSON inspection in the session folder.
Before releasing, the selected tray slot must be visibly empty and all occupied
cells of the held piece must show matching interior color and a substantial
change from their originally empty target cells. This is a conservative visual
check, not a replacement for post-release board/tray verification.

If the preview fails, the player moves the pointer below the board and lifts
there to cancel, instead of releasing at an unverified board position. Capture
errors and interruption also attempt this cancellation. Failed/cancelled input
cannot produce a verified training label.

After release or cancellation, the player waits for the exact expected board
and tray. If that cannot be verified, an automatic retry is allowed only after
the **full eight-second observation window**, at least two unchanged readings,
and **no changed or unreadable state** in that window. A second preflight check
must still match the original state. A retry uses a slower gesture and another
occupied pickup cell when the piece has one. No retry is allowed after a
misplaced piece, uncertain state, transport/capture error, or changed preflight.

One retry is enabled by default (at most two attempts per logical move):

```sh
python -u live.py --play --moves 100
```

Disable retries while retaining held-piece verification, or explicitly choose
the retry limit (maximum three retries):

```sh
python -u live.py --play --moves 100 --drag-retries 0
python -u live.py --play --moves 100 --drag-retries 1 --collect-verified
```

The terminal prints each attempt, preview decision, unchanged-state retry, and
final verification. Move records include attempt numbers, pickup indices, and
per-attempt before/held screenshot paths. The ordinary step before/after files
remain available for compatibility. The saved gray-theme corner failure was
successfully replayed live with this check: all five held target cells matched,
the piece was released, the expected row cleared, and the next tray verified.


To play without a move-count limit:

```sh
python -u live.py --play --moves 0
```

Add `--collect-verified` to also collect verified training examples. Unlimited
mode still stops on no legal moves, recognition/verification failures, or Ctrl+C;
it does not restart games or dismiss ads. Positive `--moves` values retain the
bounded behavior, and the default remains one move.
