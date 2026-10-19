"""Collect unlabelled and outcome-verified piece crops without modifying models."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / 'captures' / 'unclassified'
DEFAULT_FAILED_DATASET = ROOT / 'captures' / 'failed_shapes'


def save_shapes(image, profile, state=None, directory=DEFAULT_DATASET, *, slots=None, event=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    saved = []
    for slot, box in enumerate(profile['tray_boxes']):
        if slots is not None and slot not in slots:
            continue
        if state is not None and state.pieces[slot] is None:
            continue
        crop = image.convert('RGB').crop(tuple(box))
        digest = hashlib.sha256(str(crop.size).encode() + crop.tobytes()).hexdigest()
        target = directory / f'{digest}.png'
        if target.exists():
            if event is not None:
                sidecar=target.with_suffix('.json')
                metadata=json.loads(sidecar.read_text()) if sidecar.exists() else {'label':None}
                events=metadata.setdefault('failure_events',[])
                if event not in events:
                    events.append(event)
                    sidecar.write_text(json.dumps(metadata,indent=2)+'\n')
            continue
        crop.save(target)
        metadata = {
            'label': None,
            'predicted_shape': state.pieces[slot] if state else None,
            'slot': slot + 1,
            'captured_at': datetime.now(timezone.utc).isoformat(),
            'screen_size': list(image.size),
            'crop_box': list(box),
            'board': f'{state.board:016x}' if state else None,
            'sha256': digest,
        }
        if event is not None:
            metadata['failure_events']=[event]
        target.with_suffix('.json').write_text(json.dumps(metadata, indent=2) + '\n')
        saved.append(target)
    return saved


DEFAULT_VERIFIED_DATASET = ROOT / 'shape_model' / 'shapes'


def save_verified_shape(before_image, after_image, profile, before, after, slot, move,
                        directory=DEFAULT_VERIFIED_DATASET, *, session=None, step=None):
    """Label only the played crop after matching actual board and tray evidence.

    Re-read both images so this function cannot promote an arbitrary prediction
    merely because its caller says the move succeeded. This is an automatic
    outcome-verified label, not a human-reviewed ground-truth annotation.
    """
    from dataclasses import asdict
    from game_player import expected_tray
    from screen_reader import read_screen
    from solver import apply_move

    if not 0 <= slot < len(before.pieces) or before.pieces[slot] != move.shape:
        raise ValueError('Played slot does not match the shape being labelled')
    expected, lines = apply_move(before.board, move.shape, move.row, move.col)
    if after.board != expected or not expected_tray(before, after, slot):
        raise ValueError('Cannot label a piece without the expected board and tray transition')
    if read_screen(before_image, profile) != before or read_screen(after_image, profile) != after:
        raise ValueError('Verification images do not match the supplied board/tray states')

    crop = before_image.convert('RGB').crop(tuple(profile['tray_boxes'][slot]))
    digest = hashlib.sha256(str(crop.size).encode() + crop.tobytes()).hexdigest()
    folder = Path(directory) / move.shape
    target = folder / f'{digest}.png'
    if target.exists():
        return None
    metadata = {
        'label': move.shape,
        'label_source': 'verified_move',
        'verification': 'board_and_tray_match',
        'verified_at': datetime.now(timezone.utc).isoformat(),
        'slot': slot + 1,
        'move': asdict(move),
        'move_coordinates': 'zero_based',
        'before_board': f'{before.board:016x}',
        'expected_board': f'{expected:016x}',
        'after_board': f'{after.board:016x}',
        'before_pieces': list(before.pieces),
        'after_pieces': list(after.pieces),
        'lines_cleared': lines,
        'screen_size': list(before_image.size),
        'crop_box': list(profile['tray_boxes'][slot]),
        'sha256': digest,
        'session': str(session) if session is not None else None,
        'step': step,
    }
    folder.mkdir(parents=True, exist_ok=True)
    crop.save(target)
    target.with_suffix('.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return target


def save_failed_shapes(image, profile, directory=DEFAULT_FAILED_DATASET, *,
                       state=None, slots=None, error=None, session=None, phase='stopped'):
    """Keep failed input apart from training data, including its failure context."""
    import numpy as np
    import re
    from screen_reader import piece_geometry, read_screen

    if image.size != tuple(profile['screen_size']):
        return []  # Profile crop coordinates would not be valid.
    pixels=np.asarray(image.convert('RGB'))
    if int(pixels.max())-int(pixels.min())<=3:
        return []  # An unavailable display contains no pieces to classify.
    if slots is None:
        match=re.search(r'Tray slot (\d+)',str(error))
        if match:
            slots=[int(match.group(1))-1]
    if state is None:
        try:
            state=read_screen(image,profile)
        except ValueError:
            # Preserve unreadable slots, but don't fill the review queue with
            # slots which can positively be recognized as empty.
            candidates=[]
            for slot in (slots if slots is not None else range(3)):
                try:
                    name,_,_=piece_geometry(image,profile,slot)
                    if name is None:
                        continue
                except ValueError:
                    pass
                candidates.append(slot)
            slots=candidates
    event={'error':str(error) if error is not None else None,
           'session':str(session) if session is not None else None,'phase':phase}
    return save_shapes(image,profile,state,directory,slots=slots,event=event)
