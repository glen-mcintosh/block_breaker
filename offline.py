"""Run reproducible solver scenarios without ADB, screenshots, or PyTorch."""
import argparse
import json
from pathlib import Path
import random

from config import shape_classes
from solver import best_moves, clear_lines, format_board, parse_board


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=Path(__file__).with_name('scenarios.json'))
    parser.add_argument('--scenario', help='Run just this named scenario')
    parser.add_argument('--random', type=int, default=0, metavar='COUNT', help='Add seeded synthetic boards')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    scenarios = json.loads(args.fixtures.read_text())
    if args.scenario:
        scenarios = [s for s in scenarios if s['name'] == args.scenario]
        if not scenarios:
            parser.error('Unknown scenario name')
    rng = random.Random(args.seed)
    for i in range(args.random):
        board = sum(1 << n for n in range(64) if rng.random() < 0.55)
        board, _ = clear_lines(board)
        scenarios.append(dict(name=f'random-{args.seed}-{i}', board=format_board(board).splitlines(),
                              pieces=rng.choices(sorted(shape_classes), k=3)))
    for scenario in scenarios:
        board = parse_board(scenario['board'])
        pieces = scenario['pieces']
        result = best_moves(board, pieces)
        print(f"\n{scenario['name']}: {', '.join(pieces)}")
        print(format_board(board))
        print(f'Placed {len(result.moves)}/{len(pieces)}; lines={result.lines_cleared}; '
              f'heuristic={result.evaluation}; {result.elapsed_ms:.1f} ms; {result.states:,} states')
        for move in result.moves:
            print(f'  piece {move.piece_index + 1} ({move.shape}) -> '
                  f'row {move.row + 1}, column {move.col + 1}; clears {move.lines_cleared}')
        print('Result:\n' + format_board(result.final_board))


if __name__ == '__main__':
    main()
