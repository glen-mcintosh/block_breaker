import json
from pathlib import Path
import random
import unittest

from config import shape_classes
from solver import (FULL, apply_move, best_moves, board_features, clear_lines,
                    evaluate, format_board, parse_board, placements)


def grid_of(board):
    return [[bool(board & (1 << (r * 8 + c))) for c in range(8)] for r in range(8)]


def reference_apply(board, shape, row, col):
    """Independent cell-based rules oracle (no production mask/clear helpers)."""
    grid = grid_of(board)
    cells = shape_classes[shape]['shape']
    h, w = cells.shape
    if row < 0 or col < 0 or row + h > 8 or col + w > 8:
        return None
    for y in range(h):
        for x in range(w):
            if cells[y, x] and grid[row + y][col + x]:
                return None
    for y in range(h):
        for x in range(w):
            if cells[y, x]:
                grid[row + y][col + x] = True
    rows = {r for r in range(8) if all(grid[r])}
    cols = {c for c in range(8) if all(grid[r][c] for r in range(8))}
    result = sum(1 << (r * 8 + c) for r in range(8) for c in range(8)
                 if grid[r][c] and r not in rows and c not in cols)
    return result, len(rows) + len(cols)


def reference_features(board):
    grid = grid_of(board)
    squares = lambda size: sum(all(not grid[r+y][c+x] for y in range(size) for x in range(size))
                               for r in range(9-size) for c in range(9-size))
    isolated = sum(not grid[r][c] and all(grid[y][x] for y, x in
                   ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if 0 <= y < 8 and 0 <= x < 8)
                   for r in range(8) for c in range(8))
    return dict(empty=sum(not v for row in grid for v in row), squares2=squares(2),
                squares3=squares(3), isolated=isolated)


def reference_best(board, pieces):
    outcomes = []
    for i, shape in enumerate(pieces):
        h, w = shape_classes[shape]['shape'].shape
        for r in range(9-h):
            for c in range(9-w):
                after = reference_apply(board, shape, r, c)
                if after is not None:
                    placed, score = reference_best(after[0], pieces[:i] + pieces[i+1:])
                    outcomes.append((placed + 1, score + 2 * after[1]))
    return max(outcomes) if outcomes else (0, evaluate(board))


class RulesTests(unittest.TestCase):
    def test_board_roundtrip_and_invalid_inputs(self):
        for board in (0, FULL, 0x8765432112345678):
            self.assertEqual(parse_board(format_board(board)), board)
        for rows in (['........'], ['xxxxxxxx'] * 8):
            with self.assertRaises(ValueError): parse_board(rows)
        for board in (-1, 1 << 64):
            with self.assertRaises(ValueError): best_moves(board, ['zz_single'])
        for pieces in ([], ['zz_single'] * 4, ['unknown']):
            with self.assertRaises(ValueError): best_moves(0, pieces)

    def test_simultaneous_cross_clear(self):
        board = parse_board(['.#######'] + ['#.......'] * 7)
        self.assertEqual(apply_move(board, 'zz_single', 0, 0), (0, 2))

    def test_boundaries_overlap_and_fixed_orientation(self):
        with self.assertRaises(ValueError): apply_move(0, 'square_2', 7, 7)
        with self.assertRaises(ValueError): apply_move(0, 'zz_single', -1, 0)
        with self.assertRaises(ValueError): apply_move(1, 'zz_single', 0, 0)
        board = FULL ^ sum(1 << (r * 8) for r in range(5))
        self.assertFalse(best_moves(board, ['line_5_h']).moves)
        self.assertTrue(best_moves(board, ['line_5_v']).moves)

    def test_all_shapes_against_reference(self):
        rng = random.Random(104)
        boards = [0] + [rng.getrandbits(64) for _ in range(6)]
        for shape, spec in shape_classes.items():
            h, w = spec['shape'].shape
            self.assertEqual(len(placements(shape)), (9-h)*(9-w))
            for p in placements(shape):
                self.assertEqual(p.mask.bit_count(), int(spec['shape'].sum()))
                for board in boards:
                    expected = reference_apply(board, shape, p.row, p.col)
                    if expected is None:
                        with self.assertRaises(ValueError): apply_move(board, shape, p.row, p.col)
                    else:
                        self.assertEqual(apply_move(board, shape, p.row, p.col), expected)

    def test_features_against_grid_reference(self):
        rng = random.Random(13)
        for board in [0, FULL, 1, FULL ^ 1] + [rng.getrandbits(64) for _ in range(250)]:
            self.assertEqual(board_features(board), reference_features(board))


class SearchTests(unittest.TestCase):
    def test_exact_search_against_independent_bruteforce(self):
        rng = random.Random(72)
        for _ in range(12):
            board, _ = clear_lines(rng.getrandbits(64))
            pieces = tuple(rng.choices(sorted(shape_classes), k=2))
            result = best_moves(board, pieces)
            self.assertEqual((len(result.moves), result.evaluation), reference_best(board, pieces))

    def test_three_piece_search_against_reference(self):
        board = parse_board(['####.###', '###.####', '##.#####', '#.######',
                             '#######.', '######.#', '#####.##', '.#######'])
        pieces = ('zz_single', 'line_2_h', 'square_2')
        result = best_moves(board, pieces)
        self.assertEqual((len(result.moves), result.evaluation), reference_best(board, pieces))

    def test_fixture_regressions_and_replay(self):
        scenarios = json.loads(Path(__file__).resolve().parents[1].joinpath('scenarios.json').read_text())
        expected_counts = {'open-board': 3, 'cross-clear': 3, 'order-matters': 3,
                           'fragmented': 1, 'no-moves': 0, 'notebook-board': 1}
        for scenario in scenarios:
            board = parse_board(scenario['board'])
            result = best_moves(board, scenario['pieces'])
            self.assertEqual(len(result.moves), expected_counts[scenario['name']])
            lines = 0
            used = set()
            for move in result.moves:
                self.assertNotIn(move.piece_index, used)
                used.add(move.piece_index)
                self.assertEqual(scenario['pieces'][move.piece_index], move.shape)
                board, cleared = reference_apply(board, move.shape, move.row, move.col)
                self.assertEqual(cleared, move.lines_cleared)
                lines += cleared
            self.assertEqual(board, result.final_board)
            self.assertEqual(lines, result.lines_cleared)
            self.assertEqual(evaluate(board) + 2 * lines, result.evaluation)

    def test_order_changes_and_replay(self):
        scenarios = json.loads(Path(__file__).resolve().parents[1].joinpath('scenarios.json').read_text())
        scenario = next(s for s in scenarios if s['name'] == 'order-matters')
        board = parse_board(scenario['board'])
        result = best_moves(board, scenario['pieces'])
        self.assertEqual(len(result.moves), 3)
        self.assertEqual(result.moves[0].piece_index, 1)
        used = set()
        for move in result.moves:
            self.assertNotIn(move.piece_index, used)
            used.add(move.piece_index)
            self.assertEqual(scenario['pieces'][move.piece_index], move.shape)
            board, lines = reference_apply(board, move.shape, move.row, move.col)
            self.assertEqual(lines, move.lines_cleared)
        self.assertEqual(board, result.final_board)

    def test_no_moves_partial_and_duplicates(self):
        board = parse_board(['#.#.#.#.', '.#.#.#.#'] * 4)
        self.assertEqual(best_moves(board, ['square_2', 'line_3_h', 'line_3_v']).moves, ())
        self.assertEqual(len(best_moves(board, ['square_2', 'line_3_h', 'zz_single']).moves), 1)
        result = best_moves(board, ['zz_single'] * 3)
        self.assertEqual({m.piece_index for m in result.moves}, {0, 1, 2})
        self.assertEqual(result.moves, best_moves(board, ['zz_single'] * 3).moves)


if __name__ == '__main__':
    unittest.main()
