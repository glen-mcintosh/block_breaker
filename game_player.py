"""Calibrated dragging and verification for the current Waydroid layout."""
from dataclasses import dataclass
import subprocess
import time

import numpy as np
from config import shape_classes
from screen_reader import piece_geometry, read_screen
from solver import apply_move


@dataclass(frozen=True)
class Drag:
    start: tuple
    end: tuple


def plan_drag(image, profile, slot, move, *, pickup_index=0):
    """Convert logical target to touch coordinates using measured lift/gain."""
    calibration = profile.get('drag')
    if not calibration or not calibration.get('calibrated'):
        raise ValueError('Drag calibration is required before playing')
    state = read_screen(image, profile)
    if state.pieces[slot] != move.shape:
        raise ValueError('Selected tray piece does not match the planned move')
    apply_move(state.board, move.shape, move.row, move.col)
    l,t,r,b = profile['tray_boxes'][slot]
    name,xs,ys = piece_geometry(image,profile,slot)
    if name != move.shape:
        raise ValueError('Piece geometry changed during drag planning')
    cells = shape_classes[move.shape]['shape']
    occupied=[(y,x) for y in range(cells.shape[0]) for x in range(cells.shape[1]) if cells[y,x]]
    row,col=occupied[pickup_index%len(occupied)]
    start = (l+float(np.mean(xs[col])), t+float(np.mean(ys[row])))
    center = (l+(float(np.mean(xs[0]))+float(np.mean(xs[-1])))/2,
              t+(float(np.mean(ys[0]))+float(np.mean(ys[-1])))/2)
    left,top,right,bottom = profile['board_box']
    dx,dy = (right-left)/8,(bottom-top)/8
    # The expanded piece stays centered on its tray bounding box on pickup,
    # shifts upward by lift_y, then tracks finger movement with measured gain.
    anchor = (center[0]-(cells.shape[1]-1)*dx/2,
              center[1]-(cells.shape[0]-1)*dy/2-calibration['lift_y'])
    target = (left+(move.col+.5)*dx,top+(move.row+.5)*dy)
    end = tuple(start[i]+(target[i]-anchor[i])/calibration['gain'] for i in range(2))
    start,end = tuple(map(round,start)),tuple(map(round,end))
    if any(not (0 <= p[0] < image.width and 0 <= p[1] < image.height) for p in (start,end)):
        raise ValueError('Drag touch position is outside the screen')
    return Drag(start,end)


class HeldPreviewError(ValueError):
    """The drag was cancelled because its held-piece evidence was insufficient."""


def inspect_held(before_image, held_image, profile, slot, move):
    """Require a lifted tray piece and its full-size interior at every target cell."""
    if held_image.size != before_image.size or held_image.size != tuple(profile['screen_size']):
        raise ValueError('Held screenshot resolution differs from calibration')
    before=read_screen(before_image,profile)
    apply_move(before.board,move.shape,move.row,move.col)
    name,xs,ys=piece_geometry(before_image,profile,slot)
    if name!=move.shape:
        raise ValueError('Source shape changed before held preview')
    cells=shape_classes[move.shape]['shape']
    source=np.asarray(before_image.convert('RGB')).astype(int)
    held=np.asarray(held_image.convert('RGB')).astype(int)
    l,t,_,_=profile['tray_boxes'][slot]
    source_colors=[]
    for row,col in zip(*np.nonzero(cells)):
        x,y=round(l+float(np.mean(xs[col]))),round(t+float(np.mean(ys[row])))
        source_colors.append(np.median(source[y-2:y+3,x-2:x+3],axis=(0,1)))
    color=np.median(source_colors,axis=0)
    try:
        lifted=piece_geometry(held_image,profile,slot)[0] is None
    except ValueError:
        lifted=False
    left,top,right,bottom=profile['board_box']
    dx,dy=(right-left)/8,(bottom-top)/8
    checks=[]
    for row,col in zip(*np.nonzero(cells)):
        x,y=round(left+(move.col+col+.5)*dx),round(top+(move.row+row+.5)*dy)
        # A large interior patch avoids accepting just a ghost edge or a block
        # which is still between cells. The target was empty in the source frame.
        patch=held[y-8:y+9,x-8:x+9]
        original=source[y-8:y+9,x-8:x+9]
        coverage=float((np.max(abs(patch-color),axis=2)<=35).mean())
        changed=float((np.max(abs(patch-original),axis=2)>25).mean())
        checks.append({'row':int(move.row+row),'col':int(move.col+col),
                       'color_coverage':coverage,'changed_coverage':changed})
    aligned=all(check['color_coverage']>=.8 and check['changed_coverage']>=.8 for check in checks)
    return {'approved':lifted and aligned,'lifted':lifted,'aligned':aligned,
            'source_rgb':color.tolist(),'target_cells':checks}


def _gesture(serial, commands, timeout=20):
    subprocess.run(['adb','-s',serial,'shell','; '.join(commands)],check=True,
                   capture_output=True,timeout=timeout)


def send_drag(serial, drag, *, before_image, profile, slot, move, capture,
              preview_path, cautious=False):
    """Hold at the target, inspect/save a preview, then release or cancel safely."""
    import json
    from pathlib import Path

    x,y=drag.start
    commands=[f'input touchscreen motionevent DOWN {x} {y}',
              'sleep 0.30' if cautious else 'sleep 0.15']
    for step in range(1,13):
        x=round(drag.start[0]+(drag.end[0]-drag.start[0])*step/12)
        y=round(drag.start[1]+(drag.end[1]-drag.start[1])*step/12)
        commands.extend([f'input touchscreen motionevent MOVE {x} {y}',
                         'sleep 0.05' if cautious else 'sleep 0.03'])
    commands.append('sleep 0.30' if cautious else 'sleep 0.15')
    held=True
    try:
        _gesture(serial,commands)
        preview=capture()
        path=Path(preview_path)
        preview.save(path)
        inspection=inspect_held(before_image,preview,profile,slot,move)
        path.with_suffix('.json').write_text(json.dumps(inspection,indent=2)+'\n')
        if not inspection['approved']:
            reason='pickup not confirmed' if not inspection['lifted'] else 'piece not aligned with target cells'
            raise HeldPreviewError(f'Held preview rejected: {reason}')
        _gesture(serial,[f'input touchscreen motionevent UP {x} {y}'],timeout=5)
        held=False
        return inspection
    finally:
        if held:
            # Cancel below the board before lifting the finger. Releasing at an
            # unverified board target could accidentally commit a different move.
            cancel_x,cancel_y=drag.start[0],before_image.height-80
            _gesture(serial,[f'input touchscreen motionevent MOVE {cancel_x} {cancel_y}',
                             'sleep 0.15',f'input touchscreen motionevent UP {cancel_x} {cancel_y}'],timeout=5)


def expected_tray(before, after, slot):
    if any(before.pieces[i] is not None for i in range(3) if i != slot):
        return after.pieces == tuple(None if i==slot else value for i,value in enumerate(before.pieces))
    # Last piece: the next tray must have arrived. We cannot predict its identities.
    return all(piece is not None for piece in after.pieces)


def wait_stable(capture, profile, timeout=8, expected_board=None, before=None, slot=None,
                allow_unchanged=False):
    if allow_unchanged and (before is None or expected_board is None):
        raise ValueError('Unchanged verification requires the original state and expected board')
    deadline=time.monotonic()+timeout
    previous=None
    last_error='No settled screen'
    unchanged_count=0
    unchanged_image=None
    uncertain=False
    while time.monotonic()<deadline:
        image=capture()
        try:
            state=read_screen(image,profile)
            if allow_unchanged:
                if state==before:
                    unchanged_count+=1
                    unchanged_image=image
                else:
                    uncertain=True
                    unchanged_count=0
            acceptable=expected_board is None or (state.board==expected_board and expected_tray(before,state,slot))
            if acceptable and state==previous:
                return image,state
            previous=state if acceptable else None
            last_error='Board/tray did not match the expected move result' if not acceptable else 'Screen still changing'
        except ValueError as error:
            uncertain=True
            unchanged_count=0
            previous=None
            last_error=str(error)
        time.sleep(.2)
    if allow_unchanged and not uncertain and unchanged_count>=2:
        return unchanged_image,before
    raise ValueError(f'Stopped waiting for a verified screen: {last_error}')
