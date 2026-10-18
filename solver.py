"""Offline, deterministic 8x8 rules and exhaustive search for up to three pieces.

Assumptions: fixed orientations, no gravity, simultaneous full-row/column clears
following each placement. Evaluation is a survival heuristic, not game points.
"""
from dataclasses import dataclass
from functools import lru_cache
from time import perf_counter

from config import shape_classes

SIZE = 8
FULL = (1 << 64) - 1
ROWS = tuple(255 << (8 * r) for r in range(8))
COLS = tuple(sum(1 << (8 * r + c) for r in range(8)) for c in range(8))
NOT_LEFT = FULL ^ COLS[0]
NOT_RIGHT = FULL ^ COLS[7]


@dataclass(frozen=True)
class Placement:
    row: int
    col: int
    mask: int


@dataclass(frozen=True)
class Move:
    piece_index: int
    shape: str
    row: int
    col: int
    lines_cleared: int


@dataclass(frozen=True)
class Result:
    moves: tuple[Move, ...]
    final_board: int
    evaluation: int
    lines_cleared: int
    states: int
    elapsed_ms: float


def validate_board(board):
    if not isinstance(board, int) or not 0 <= board <= FULL:
        raise ValueError('Board must be an unsigned 64-bit integer')


def parse_board(rows):
    if isinstance(rows, str):
        rows = rows.split()
    if len(rows) != 8 or any(len(row) != 8 for row in rows):
        raise ValueError('Board must contain eight rows of eight cells')
    if any(cell not in '.#01' for row in rows for cell in row):
        raise ValueError('Use . or 0 for empty cells and # or 1 for occupied cells')
    return sum(1 << (r * 8 + c) for r, row in enumerate(rows)
               for c, cell in enumerate(row) if cell in '#1')


def format_board(board):
    validate_board(board)
    return '\n'.join(''.join('#' if board & (1 << (r * 8 + c)) else '.'
                             for c in range(8)) for r in range(8))


@lru_cache(maxsize=None)
def placements(shape):
    if shape not in shape_classes:
        raise ValueError(f'Unknown shape: {shape}')
    cells = shape_classes[shape]['shape']
    height, width = cells.shape
    return tuple(Placement(r, c, sum(1 << ((r + y) * 8 + c + x)
                                     for y in range(height) for x in range(width)
                                     if cells[y, x]))
                 for r in range(9 - height) for c in range(9 - width))


def clear_lines(board):
    """Compute all completed lines before removing their union."""
    cleared = count = 0
    for mask in ROWS + COLS:
        if board & mask == mask:
            cleared |= mask
            count += 1
    return board & ~cleared, count


def apply_move(board, shape, row, col):
    validate_board(board)
    placement = next((p for p in placements(shape) if (p.row, p.col) == (row, col)), None)
    if placement is None:
        raise ValueError('Placement is outside the board')
    if board & placement.mask:
        raise ValueError('Placement overlaps occupied cells')
    return clear_lines(board | placement.mask)


def board_features(board):
    empty = FULL ^ board
    # Bits mark top-left corners. Column masks prevent wraparound between rows.
    pairs = empty & (empty >> 1) & NOT_RIGHT
    squares2 = pairs & (pairs >> 8)
    triples = pairs & (empty >> 2) & ~(COLS[6] | COLS[7])
    squares3 = triples & (triples >> 8) & (triples >> 16)
    neighbors = (((empty << 1) & NOT_LEFT) | ((empty >> 1) & NOT_RIGHT)
                 | (empty << 8) | (empty >> 8))
    isolated = empty & ~neighbors
    return dict(empty=empty.bit_count(), squares2=squares2.bit_count(),
                squares3=squares3.bit_count(), isolated=isolated.bit_count())


def evaluate(board):
    f = board_features(board)
    return f['empty'] + 4 * f['squares2'] + 10 * f['squares3'] - 8 * f['isolated']


def best_moves(board, shapes):
    """Maximize (pieces placed, board heuristic + 2 * total cleared lines).

    Exhaustively examines legal orders/positions; ties are deterministic. Returns
    the best partial sequence if using every piece is impossible. Cache lifetime
    is one call. Runtime varies by board; there is no search cutoff.
    """
    validate_board(board)
    shapes = tuple(shapes)
    if not 1 <= len(shapes) <= 3:
        raise ValueError('Supply one to three pieces')
    options = tuple(placements(s) for s in shapes)
    started = perf_counter()

    @lru_cache(maxsize=None)
    def leaf(state):
        return evaluate(state)

    @lru_cache(maxsize=None)
    def search(state, remaining):
        best = None
        seen_shapes = set()
        for i, shape in enumerate(shapes):
            if not remaining & (1 << i) or shape in seen_shapes:
                continue
            seen_shapes.add(shape)
            for p in options[i]:
                if state & p.mask:
                    continue
                after, lines = clear_lines(state | p.mask)
                tail, end, value, total_lines = search(after, remaining ^ (1 << i))
                value += 2 * lines
                rank = (1 + len(tail), value)
                if best is None or rank > best[0]:
                    move = Move(i, shape, p.row, p.col, lines)
                    best = (rank, (move,) + tail, end, value, lines + total_lines)
        if best is None:
            return (), state, leaf(state), 0
        return best[1:]

    moves, final, value, lines = search(board, (1 << len(shapes)) - 1)
    result = Result(moves, final, value, lines, search.cache_info().misses,
                    (perf_counter() - started) * 1000)
    search.cache_clear()
    leaf.cache_clear()
    return result
