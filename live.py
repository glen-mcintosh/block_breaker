"""Read Block Blast, collect tray crops, and optionally play verified moves."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from io import BytesIO
from itertools import count
import json
from pathlib import Path
import subprocess
import time
from uuid import uuid4

from PIL import Image
from game_player import HeldPreviewError, expected_tray, plan_drag, send_drag, wait_stable
from screen_reader import DEFAULT_PROFILE, annotate, load_profile, read_screen
from shape_capture import (DEFAULT_DATASET, DEFAULT_VERIFIED_DATASET, DEFAULT_FAILED_DATASET,
                           save_shapes, save_verified_shape, save_failed_shapes)
from solver import apply_move, best_moves, format_board


def resolve_device(serial=None):
    output = subprocess.run(['adb', 'devices'], check=True, capture_output=True, text=True,timeout=10).stdout
    devices = [line.split()[0] for line in output.splitlines()[1:]
               if len(line.split()) >= 2 and line.split()[1] == 'device']
    if serial is None:
        if len(devices) != 1:
            raise ValueError(f'Expected one authorized ADB device, found {devices}. Use --serial or adb connect.')
        return devices[0]
    if serial not in devices:
        raise ValueError(f'ADB device {serial} is not connected and authorized')
    return serial


def capture(serial=None):
    serial = serial or resolve_device()
    png = subprocess.run(['adb', '-s', serial, 'exec-out', 'screencap', '-p'],
                         check=True, capture_output=True, timeout=20).stdout
    return Image.open(BytesIO(png)).convert('RGB')


def save_preview(image, profile, state, output, move=None):
    image.save(output/'latest.png')
    annotate(image, profile, state, move).save(output/'annotated.png')


def describe(state):
    print('Board:\n' + format_board(state.board), flush=True)
    print('Tray:', ', '.join(f'{i+1}: {name or "empty"}' for i,name in enumerate(state.pieces)),flush=True)


def play(serial, profile, output, dataset, moves, *, collect_verified=False,
         verified_dataset=DEFAULT_VERIFIED_DATASET, failed_dataset=DEFAULT_FAILED_DATASET,
         drag_retries=1):
    if moves<0:
        raise ValueError('moves must be zero (unlimited) or positive')
    if not 0<=drag_retries<=3:
        raise ValueError('drag_retries must be between 0 and 3')
    session = output / ('session-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid4().hex[:6])
    session.mkdir()
    grab=lambda: capture(serial)
    last_image=None
    record=None
    pending=None
    try:
        steps=count(1) if moves==0 else range(1,moves+1)
        for step in steps:
            image,state=wait_stable(grab,profile)
            last_image=image
            save_preview(image,profile,state,output)
            describe(state)
            slots=[i for i,name in enumerate(state.pieces) if name is not None]
            if not slots:
                raise ValueError('No pieces detected; no move sent')
            result=best_moves(state.board,[state.pieces[i] for i in slots])
            if not result.moves:
                print('No legal move found. Stopped.',flush=True)
                return
            move=result.moves[0]
            slot=slots[move.piece_index]
            # Recheck after search, since a human or the game may have changed the state.
            fresh,current=wait_stable(grab,profile)
            if current!=state:
                raise ValueError('Screen changed while solving; no move sent')
            expected,_=apply_move(state.board,move.shape,move.row,move.col)
            fresh.save(session/f'{step:04d}-before.png')
            save_preview(fresh,profile,state,output,move)
            for attempt in range(1,drag_retries+2):
                if attempt>1:
                    fresh,current=wait_stable(grab,profile)
                    if current!=state:
                        raise ValueError('Screen changed before retry; no second drag sent')
                drag=plan_drag(fresh,profile,slot,move,pickup_index=attempt-1)
                before_path=session/f'{step:04d}-attempt-{attempt}-before.png'
                fresh.save(before_path)
                preview_path=session/f'{step:04d}-attempt-{attempt}-held.png'
                record={'step':step,'attempt':attempt,'slot':slot+1,'move':asdict(move),'drag':asdict(drag),
                        'before_board':f'{state.board:016x}','expected_board':f'{expected:016x}',
                        'before_pieces':state.pieces,'search_ms':result.elapsed_ms,'status':'sent',
                        'held_preview':str(preview_path),'before_image':str(before_path),'pickup_index':attempt-1}
                with (session/'moves.jsonl').open('a') as log:
                    log.write(json.dumps(record)+'\n')
                print(f'Move {step}, attempt {attempt}: tray {slot+1} ({move.shape}) -> '
                      f'row {move.row+1}, column {move.col+1}; touch {drag.start} -> {drag.end}',flush=True)
                pending=(fresh,state,slot)
                preview_error=None
                try:
                    send_drag(serial,drag,before_image=fresh,profile=profile,slot=slot,move=move,
                              capture=grab,preview_path=preview_path,cautious=attempt>1)
                    print('Held preview matched; released piece.',flush=True)
                except HeldPreviewError as error:
                    preview_error=str(error)
                    print(f'{error}; cancelled drag. Checking board before any retry.',flush=True)
                # An unchanged result is returned only after the full timeout,
                # two matching observations, and no changed/unreadable states.
                after_image,after=wait_stable(grab,profile,expected_board=expected,before=state,slot=slot,
                                              allow_unchanged=True)
                if after!=state:
                    if after.board!=expected or not expected_tray(state,after,slot):
                        raise ValueError('Unexpected board after drag; no retry sent')
                    break
                after_image.save(session/f'{step:04d}-attempt-{attempt}-unchanged.png')
                record.update(status='unchanged',preview_error=preview_error)
                with (session/'moves.jsonl').open('a') as log:
                    log.write(json.dumps(record)+'\n')
                save_failed_shapes(fresh,profile,failed_dataset,state=state,slots=[slot],
                                   error=preview_error or 'Drag left board and tray unchanged',
                                   session=session,phase=f'unchanged_attempt_{attempt}')
                if attempt>drag_retries:
                    raise ValueError(f'Drag left board and tray unchanged after {attempt} attempt(s); stopped')
                print('Board and tray confirmed unchanged; retrying with a slower drag '
                      'and an alternate pickup where available.',flush=True)
            last_image=after_image
            after_image.save(session/f'{step:04d}-after.png')
            save_preview(after_image,profile,after,output)
            pending=None
            record.update(status='verified',after_pieces=after.pieces,preview_error=preview_error)
            with (session/'moves.jsonl').open('a') as log:
                log.write(json.dumps(record)+'\n')
            print(f'Move {step} verified.',flush=True)
            if collect_verified:
                labelled=save_verified_shape(fresh,after_image,profile,state,after,slot,move,
                                             verified_dataset,session=session,step=step)
                if labelled is not None:
                    print(f'Verified training crop: {labelled}',flush=True)
                else:
                    print('Verified training crop already exists; duplicate skipped.',flush=True)
    except (ValueError, OSError, subprocess.SubprocessError, KeyboardInterrupt) as error:
        failure={'error_type':type(error).__name__,'error':str(error),'last_move':record}
        (session/'failure.json').write_text(json.dumps(failure,indent=2)+'\n')
        if pending is not None and not isinstance(error,KeyboardInterrupt):
            source,source_state,slot=pending
            save_failed_shapes(source,profile,failed_dataset,state=source_state,slots=[slot],
                               error=error,session=session,phase='before_unverified_move')
        try:
            failed=grab()
            failed.save(session/'stopped.png')
            if not isinstance(error,KeyboardInterrupt):
                save_failed_shapes(failed,profile,failed_dataset,error=error,session=session)
        except (OSError,ValueError,subprocess.SubprocessError):
            if last_image is not None:
                last_image.save(session/'last-readable.png')
        raise
    finally:
        print(f'Play log: {session}',flush=True)


def watch(serial, profile, output, dataset, interval, failed_dataset=DEFAULT_FAILED_DATASET):
    """Collect settled observations while the human plays; send no input."""
    previous = saved_state = None
    print('Watching for settled boards and saving tray crops. Ctrl+C to stop.',flush=True)
    while True:
        image = capture(serial)
        try:
            state = read_screen(image,profile)
        except ValueError as error:
            save_failed_shapes(image,profile,failed_dataset,error=error,phase='watch')
            previous = None
            time.sleep(interval)
            continue
        if state == previous and state != saved_state:
            saved = save_shapes(image,profile,state,dataset)
            save_preview(image,profile,state,output)
            print(f'Saved {len(saved)} new unclassified crops.',flush=True)
            saved_state = state
        previous = state
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, help='Read a saved screenshot instead of ADB')
    parser.add_argument('--serial', help='ADB device serial, for example 192.168.240.112:5555')
    parser.add_argument('--profile', type=Path, default=DEFAULT_PROFILE)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('captures'))
    parser.add_argument('--dataset', type=Path, default=DEFAULT_DATASET,help='Unclassified crop directory for --watch (default: captures/unclassified/)')
    parser.add_argument('--failed-dataset',type=Path,default=DEFAULT_FAILED_DATASET,
                        help='Failed-piece review directory (default: captures/failed_shapes/)')
    parser.add_argument('--collect-verified',action='store_true',
                        help='With --play, label the played piece only after board/tray verification')
    parser.add_argument('--verified-dataset',type=Path,default=DEFAULT_VERIFIED_DATASET,
                        help='Training class folders for verified crops (default: shape_model/shapes/)')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--play',action='store_true',help='Send calibrated drags and verify each result')
    mode.add_argument('--watch',action='store_true',help='Collect crops while you play manually; sends no input')
    parser.add_argument('--interval',type=float,default=.5,help='Watch polling interval in seconds')
    parser.add_argument('--drag-retries',type=int,default=1,choices=range(0,4),
                        help='Retries after a proven unchanged board/tray (default: 1, maximum: 3)')
    parser.add_argument('--moves',type=int,default=1,help='Maximum moves to play; 0 means unlimited (default: 1)')
    args = parser.parse_args()
    if (args.play or args.watch) and args.image:
        parser.error('--play/--watch cannot be used with a saved image')
    if args.collect_verified and not args.play:
        parser.error('--collect-verified requires --play')
    if args.interval<=0:
        parser.error('--interval must be positive')
    if args.moves<0:
        parser.error('--moves must be zero (unlimited) or positive')
    try:
        profile = load_profile(args.profile)
        args.output.mkdir(parents=True,exist_ok=True)
        if args.watch:
            watch(resolve_device(args.serial),profile,args.output,args.dataset,args.interval,args.failed_dataset)
            return
        if args.play:
            play(resolve_device(args.serial),profile,args.output,args.dataset,args.moves,
                 collect_verified=args.collect_verified,verified_dataset=args.verified_dataset,failed_dataset=args.failed_dataset,drag_retries=args.drag_retries)
            return
        image = Image.open(args.image).convert('RGB') if args.image else capture(args.serial)
        image.save(args.output/'latest.png')
        try:
            state = read_screen(image, profile)
        except ValueError as error:
            save_failed_shapes(image,profile,args.failed_dataset,error=error,phase='analysis')
            raise
        describe(state)
        slots = [i for i, name in enumerate(state.pieces) if name is not None]
        result = best_moves(state.board, [state.pieces[i] for i in slots]) if slots else None
        if result:
            print(f'Search: {result.elapsed_ms:.1f} ms; {len(result.moves)}/{len(slots)} pieces; '
                  f'{result.lines_cleared} lines; heuristic {result.evaluation}')
            for move in result.moves:
                print(f'Piece {slots[move.piece_index]+1} ({move.shape}): '
                      f'row {move.row+1}, column {move.col+1}; clears {move.lines_cleared}')
        else:
            print('No pieces detected. Wait for the next tray and capture again.')
        first = result.moves[0] if result and result.moves else None
        save_preview(image,profile,state,args.output,first)
        print(f'Calibration preview: {args.output / "annotated.png"}')
        print('Read-only analysis; no pieces were moved.')
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f'Cannot analyze/play screen: {error}\n')
    except KeyboardInterrupt:
        parser.exit(130,'Stopped by user.\n')


if __name__ == '__main__':
    main()
