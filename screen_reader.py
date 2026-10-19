"""Read the calibrated Block Blast board and tray without a trained classifier."""
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from config import shape_classes

DEFAULT_PROFILE = Path(__file__).with_name('screen_profile.json')


@dataclass(frozen=True)
class ScreenState:
    board: int
    pieces: tuple  # Shape name or None for each of the three tray slots.


def load_profile(path=DEFAULT_PROFILE):
    return json.loads(Path(path).read_text())


def select_profile(image, profile):
    if image.size != tuple(profile['screen_size']):
        raise ValueError(f"Screen is {image.size}; calibration expects {profile['screen_size']}")
    if profile.get('recognition') == 'adaptive' or 'variants' not in profile:
        return profile
    pixel = np.array(image.convert('RGB').getpixel(tuple(profile['theme_probe'])))
    candidates = [profile] + [dict(profile, **variant) for variant in profile['variants']]
    matches = [p for p in candidates if np.max(abs(pixel-p['background_rgb'])) < 25]
    if len(matches) != 1:
        raise ValueError('Unknown theme or covered screen; capture settled gameplay or recalibrate')
    return matches[0]


def _runs(values):
    indices = np.flatnonzero(values)
    return [part for part in np.split(indices, np.where(np.diff(indices) > 1)[0] + 1)
            if len(part)]


def piece_mask(crop, profile):
    """Locate block interiors using the crop's own background and dominant color."""
    if profile.get('recognition') != 'adaptive':
        palette = profile.get('filled_palette', [profile['filled_rgb']])
        return np.logical_or.reduce([
            np.max(np.abs(crop-color),axis=2) < profile['piece_color_tolerance']
            for color in palette])
    # The calibrated side margins remain outside the pieces. Sampling each row
    # handles vertical gradients without assuming a particular background hue.
    background = np.median(np.concatenate((crop[:,:4],crop[:,-4:]),axis=1),axis=1)[:,None,:]
    foreground = np.max(abs(crop-background),axis=2) > 30
    if foreground.sum() < 40:
        return np.zeros(crop.shape[:2],dtype=bool)
    colors = crop[foreground]
    # RGB565 screenshot dithering splits nearly identical interior colors;
    # quantizing merges those into a stable dominant bin. Bevels and shadows
    # usually occupy fewer pixels than the repeated flat block interiors.
    bins = (colors//8).astype(int)
    unique,counts = np.unique(bins,axis=0,return_counts=True)
    key = unique[np.argmax(counts)]
    color = np.median(colors[np.all(bins==key,axis=1)],axis=0)
    return (np.max(abs(crop-color),axis=2) < 18) & foreground


def _decode_piece_mask(mask, profile):
    if not mask.any():
        return None, [], []
    xs = [run for run in _runs(mask.sum(axis=0) >= 4) if len(run) >= 6]
    ys = [run for run in _runs(mask.sum(axis=1) >= 4) if len(run) >= 6]
    if not xs or not ys or len(xs) > 5 or len(ys) > 5:
        raise ValueError('Unrecognized tray pixels; wait for animations or recalibrate')
    # Require regular, roughly square block interiors rather than arbitrary text/art.
    widths = [len(run) for run in xs + ys]
    if min(widths) < 6 or max(widths) > 25 or max(widths) > 1.5 * min(widths):
        raise ValueError('Irregular piece blocks; capture again or recalibrate')
    for runs in (xs, ys):
        if len(runs) > 1:
            spacings = np.diff([np.mean(run) for run in runs])
            if np.any(abs(spacings - 22.25) > 3.5):
                raise ValueError('Irregular piece spacing')
    cells = np.zeros((len(ys), len(xs)), dtype=int)
    explained = np.zeros_like(mask)
    for r, y in enumerate(ys):
        for c, x in enumerate(xs):
            region = np.ix_(y, x)
            fraction = mask[region].mean()
            if 0.1 < fraction < 0.6:
                raise ValueError('Ambiguous piece cell; capture again')
            cells[r, c] = fraction >= 0.6
            explained[region] = True
    if (mask & ~explained).sum() > mask.sum() * 0.1:
        raise ValueError('Unexplained pixels outside piece grid')
    matches = [name for name, spec in shape_classes.items()
               if np.array_equal(cells, spec['shape'])]
    if len(matches) != 1:
        raise ValueError(f'Unknown piece arrangement: {cells.tolist()}')
    return matches[0], xs, ys


def _cluster_masks(crop):
    """Merge nearby interior colors before counting them against shadow colors.

    RGB565 dithering can split a light tile into several bins while a large
    neutral shadow wins a single-bin vote. Counting neighboring bins together
    avoids selecting that shadow as the piece's interior.
    """
    background = np.median(np.concatenate((crop[:,:4],crop[:,-4:]),axis=1),axis=1)[:,None,:]
    foreground = np.max(abs(crop-background),axis=2)>30
    colors = crop[foreground]
    if not len(colors):
        return
    bins = colors//8
    unique,counts = np.unique(bins,axis=0,return_counts=True)
    representatives = unique*8+4
    weights = np.array([counts[np.max(abs(representatives-color),axis=1)<=24].sum()
                        for color in representatives])
    seen = set()
    for i in np.argsort(-weights,kind='stable'):
        neighbors = np.max(abs(colors-representatives[i]),axis=1)<=24
        color = np.median(colors[neighbors],axis=0)
        key = tuple(color)
        if key in seen:
            continue
        seen.add(key)
        yield (np.max(abs(crop-color),axis=2)<18) & foreground
        if len(seen)>=5:
            break


def _piece_geometry(crop, profile):
    mask = piece_mask(crop,profile)
    if not mask.any() and profile.get('recognition') != 'adaptive':
        background = np.median(crop,axis=(0,1))
        if (np.max(abs(crop-background),axis=2)>50).sum()>=40:
            raise ValueError('Unknown-colored piece or overlay in tray; saved for review')
    try:
        return _decode_piece_mask(mask,profile)
    except ValueError as original:
        if profile.get('recognition') != 'adaptive':
            raise
        # Keep already-successful detections and their calibrated pickup points.
        # Every fallback must pass the same size/grid/coverage/catalog checks.
        for candidate in _cluster_masks(crop):
            try:
                result = _decode_piece_mask(candidate,profile)
                if result[0] is not None:
                    return result
            except ValueError:
                continue
        raise original


def _piece(crop, profile):
    return _piece_geometry(crop,profile)[0]


def piece_geometry(image, profile, slot):
    profile = select_profile(image,profile)
    box = profile['tray_boxes'][slot]
    crop = np.asarray(image.convert('RGB').crop(tuple(box))).astype(int)
    return _piece_geometry(crop,profile)


def _adaptive_board(pixels, profile):
    left,top,right,bottom = profile['board_box']
    dx,dy = (right-left)/8,(bottom-top)/8
    centers,labels = [],[]
    for row in range(8):
        for col in range(8):
            x,y = round(left+(col+.5)*dx),round(top+(row+.5)*dy)
            offsets = [(0,0),(0,-round(.4*dy)),(0,round(.4*dy)),
                       (-round(.4*dx),0),(round(.4*dx),0)]
            patches = [np.median(pixels[y+oy-1:y+oy+2,x+ox-1:x+ox+2],axis=(0,1))
                       for ox,oy in offsets]
            center,upper,lower,west,east = patches
            flat = np.max(np.ptp(patches,axis=0))
            vertical = np.max(abs(upper-lower))
            horizontal = np.max(abs(west-east))
            # Filled blocks have directional bevels. Empty cell interiors are
            # flat, irrespective of the current theme's absolute RGB values.
            labels.append(1 if vertical>=20 and horizontal>=10 else 0 if flat<=18 else -1)
            centers.append(center)
    empty = [center for center,label in zip(centers,labels) if label==0]
    if empty:
        baseline = np.median(empty,axis=0)
        for i,(center,label) in enumerate(zip(centers,labels)):
            if label==0 and np.max(abs(center-baseline))>25:
                labels[i] = -1
    for i,label in enumerate(labels):
        if label==-1:
            raise ValueError(f'Ambiguous board cell at row {i//8+1}, column {i%8+1}; '
                             'block edges do not match settled gameplay')
    return sum(1<<i for i,label in enumerate(labels) if label==1)


def read_screen(image, profile):
    if image.size != tuple(profile['screen_size']):
        raise ValueError(f"Screen is {image.size}; calibration expects {profile['screen_size']}")
    profile = select_profile(image, profile)
    pixels = np.asarray(image.convert('RGB')).astype(int)
    if np.max(pixels)-np.min(pixels)<=3:
        raise ValueError('Screen is blank/unavailable; wake Waydroid or reopen the game')
    if profile.get('recognition') == 'adaptive':
        board = _adaptive_board(pixels,profile)
    else:
        left, top, right, bottom = profile['board_box']
        pitch_x, pitch_y = (right-left)/8, (bottom-top)/8
        board = 0
        for row in range(8):
            for col in range(8):
                x, y = round(left+(col+.5)*pitch_x), round(top+(row+.5)*pitch_y)
                sample = np.median(pixels[y-2:y+3, x-2:x+3], axis=(0, 1))
                empty = np.max(abs(sample-profile['empty_rgb'])) <= profile['board_color_tolerance']
                filled = any(np.max(abs(sample-color)) <= profile['board_color_tolerance']
                             for color in profile.get('filled_palette', [profile['filled_rgb']]))
                if empty == filled:
                    raise ValueError(f'Ambiguous board cell at row {row+1}, column {col+1}: {sample.tolist()}')
                if filled:
                    board |= 1 << (row*8+col)
    pieces=[]
    for slot,(l,t,r,b) in enumerate(profile['tray_boxes'],1):
        try:
            pieces.append(_piece(pixels[t:b,l:r],profile))
        except ValueError as error:
            raise ValueError(f'Tray slot {slot}: {error}') from error
    return ScreenState(board,tuple(pieces))


def annotate(image, profile, state, move=None):
    result = image.convert('RGB').copy()
    draw = ImageDraw.Draw(result)
    l,t,r,b = profile['board_box']
    dx,dy = (r-l)/8,(b-t)/8
    for row in range(8):
        for col in range(8):
            x,y=l+(col+.5)*dx,t+(row+.5)*dy
            color = 'cyan' if state.board & (1 << (row*8+col)) else 'lime'
            draw.ellipse((x-3,y-3,x+3,y+3),fill=color)
    for box, name in zip(profile['tray_boxes'], state.pieces):
        draw.rectangle(box,outline='cyan',width=2)
        draw.text((box[0]+2,box[1]+2),name or 'empty',fill='black',stroke_width=1,stroke_fill='white')
    if move:
        for y,row in enumerate(shape_classes[move.shape]['shape']):
            for x,cell in enumerate(row):
                if cell:
                    left,top=l+(move.col+x)*dx,t+(move.row+y)*dy
                    draw.rectangle((left+3,top+3,left+dx-3,top+dy-3),outline='yellow',width=3)
    return result
