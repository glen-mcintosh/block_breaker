"""Replay saved screens against logged board/tray states; never connects to ADB."""
import argparse
import json
from pathlib import Path

from PIL import Image
from screen_reader import load_profile,read_screen


def audit(root, profile):
    checked=0
    failures=[]
    for log in sorted(root.glob('session-*/moves.jsonl')):
        records=[json.loads(line) for line in log.read_text().splitlines()]
        verified={r['step']:r for r in records if r['status']=='verified'}
        for step,record in verified.items():
            for phase in ('before','after'):
                path=Path(record['before_image']) if phase=='before' and record.get('before_image') else log.parent/f'{step:04d}-{phase}.png'
                if not path.exists():
                    continue
                board=record['before_board'] if phase=='before' else record['expected_board']
                pieces=record['before_pieces'] if phase=='before' else record['after_pieces']
                try:
                    with Image.open(path) as image:
                        actual=read_screen(image,profile)
                    if actual.board!=int(board,16) or actual.pieces!=tuple(pieces):
                        failures.append({'path':str(path),'expected_board':board,'expected_pieces':pieces,
                                         'actual_board':f'{actual.board:016x}','actual_pieces':actual.pieces})
                except (ValueError,OSError) as error:
                    failures.append({'path':str(path),'error':str(error)})
                checked+=1
                if checked%100==0:
                    print(f'Checked {checked} screens; {len(failures)} mismatches/errors',flush=True)
    return {'checked':checked,'failures':failures}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures',type=Path,default=Path(__file__).with_name('captures'))
    args=parser.parse_args()
    result=audit(args.captures,load_profile())
    destination=args.captures/'audit-report.json'
    destination.write_text(json.dumps(result,indent=2)+'\n')
    print(f"Checked {result['checked']} screens; {len(result['failures'])} mismatches/errors. Report: {destination}")
    raise SystemExit(bool(result['failures']))


if __name__=='__main__':
    main()
