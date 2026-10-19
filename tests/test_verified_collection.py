import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image,ImageDraw

from game_player import Drag
from screen_reader import load_profile,read_screen
from shape_capture import save_verified_shape
from solver import Move,apply_move


def tile(draw,box,color):
    l,t,r,b=box
    shade=lambda amount:tuple(max(0,min(255,value+amount)) for value in color)
    draw.rectangle(box,fill=color)
    draw.rectangle((l,t,r,t+5),fill=shade(50))
    draw.rectangle((l,b-5,r,b),fill=shade(-50))
    draw.rectangle((l,t+6,l+5,b-6),fill=shade(25))
    draw.rectangle((r-5,t+6,r,b-6),fill=shade(-25))


def frames(board=0):
    profile=load_profile()
    color=(239,97,140)
    background=(239,166,173)
    before_image=Image.new('RGB',(450,1000),background)
    draw=ImageDraw.Draw(before_image)
    draw.rectangle(profile['board_box'],fill=(123,60,66))
    for r in range(8):
        for c in range(8):
            if board & (1<<(r*8+c)):
                tile(draw,(27+c*50,244+r*50,72+c*50,289+r*50),color)
    draw.rectangle((60,740,74,754),fill=color)
    for y in (740,762):
        for x in (210,232):
            draw.rectangle((x,y,x+14,y+14),fill=color)
    before=read_screen(before_image,profile)
    final,lines=apply_move(board,'zz_single',0,0)
    move=Move(0,'zz_single',0,0,lines)
    after_image=before_image.copy()
    draw=ImageDraw.Draw(after_image)
    draw.rectangle(profile['board_box'],fill=(123,60,66))
    for r in range(8):
        for c in range(8):
            if final & (1<<(r*8+c)):
                tile(draw,(27+c*50,244+r*50,72+c*50,289+r*50),color)
    l,t,r,b=profile['tray_boxes'][0]
    draw.rectangle((l,t,r-1,b-1),fill=background)
    after=read_screen(after_image,profile)
    return profile,before_image,after_image,before,after,move


class VerifiedCollectionTests(unittest.TestCase):
    def test_only_played_crop_is_labelled_with_evidence_and_deduplicated(self):
        profile,before_image,after_image,before,after,move=frames()
        with tempfile.TemporaryDirectory() as directory:
            target=save_verified_shape(before_image,after_image,profile,before,after,0,move,directory,
                                       session='example-session',step=3)
            self.assertEqual(target.parent.name,'zz_single')
            self.assertEqual(len(list(Path(directory).rglob('*.png'))),1)
            self.assertFalse((Path(directory)/'square_2').exists())
            with Image.open(target) as crop:
                self.assertEqual(crop.tobytes(),before_image.crop(tuple(profile['tray_boxes'][0])).tobytes())
            data=json.loads(target.with_suffix('.json').read_text())
            self.assertEqual(data['label'],'zz_single')
            self.assertEqual(data['label_source'],'verified_move')
            self.assertEqual(data['after_board'],data['expected_board'])
            self.assertEqual(data['after_pieces'],[None,'square_2',None])
            self.assertEqual(data['step'],3)
            self.assertIsNone(save_verified_shape(before_image,after_image,profile,before,after,0,move,directory))

    def test_line_clear_is_verified_before_labelling(self):
        profile,im1,im2,before,after,move=frames(254)
        self.assertEqual(after.board,0)
        with tempfile.TemporaryDirectory() as directory:
            target=save_verified_shape(im1,im2,profile,before,after,0,move,directory)
            data=json.loads(target.with_suffix('.json').read_text())
            self.assertEqual(data['lines_cleared'],1)
            self.assertEqual(data['after_board'],'0000000000000000')

    def test_wrong_board_or_tray_never_creates_a_label(self):
        from screen_reader import ScreenState
        profile,im1,im2,before,after,move=frames()
        for wrong in (ScreenState(2,after.pieces),ScreenState(after.board,before.pieces)):
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError,'expected board and tray'):
                    save_verified_shape(im1,im2,profile,before,wrong,0,move,directory)
                self.assertEqual(list(Path(directory).iterdir()),[])

    def test_incorrect_image_or_slot_never_creates_a_label(self):
        profile,im1,im2,before,after,move=frames()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'images do not match'):
                save_verified_shape(im1,im1,profile,before,after,0,move,directory)
            with self.assertRaisesRegex(ValueError,'slot'):
                save_verified_shape(im1,im2,profile,before,after,1,move,directory)
            self.assertEqual(list(Path(directory).iterdir()),[])


class PlayerCollectionTests(unittest.TestCase):
    def test_play_collection_is_opt_in_and_runs_after_verification(self):
        from live import play
        profile,im1,im2,before,after,move=frames()
        for enabled in (False,True):
            with self.subTest(enabled=enabled),tempfile.TemporaryDirectory() as folder:
                root=Path(folder)
                observations=[(im1,before),(im1,before),(im2,after)]
                with patch('live.wait_stable',side_effect=observations),patch('live.best_moves',return_value=SimpleNamespace(moves=[move],elapsed_ms=0)),patch('live.plan_drag',return_value=Drag((1,1),(2,2))),patch('live.send_drag') as send,contextlib.redirect_stdout(io.StringIO()):
                    play('test',profile,root,root/'unclassified',1,collect_verified=enabled,verified_dataset=root/'verified',failed_dataset=root/'failed')
                send.assert_called_once()
                self.assertFalse((root/'unclassified').exists())
                self.assertFalse((root/'failed').exists())
                labelled=list((root/'verified').rglob('*.png'))
                self.assertEqual(len(labelled),int(enabled))
                if enabled:
                    self.assertEqual(labelled[0].parent.name,'zz_single')

    def test_failed_move_cannot_promote_a_training_crop(self):
        from live import play
        profile,im1,im2,before,after,move=frames()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            observations=[(im1,before),(im1,before),ValueError('verification failed')]
            with patch('live.wait_stable',side_effect=observations),patch('live.best_moves',return_value=SimpleNamespace(moves=[move],elapsed_ms=0)),patch('live.plan_drag',return_value=Drag((1,1),(2,2))),patch('live.send_drag'),patch('live.capture',side_effect=OSError('offline')),patch('live.save_verified_shape') as collector,contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError,'verification failed'):
                    play('test',profile,root,root/'unclassified',1,collect_verified=True,verified_dataset=root/'verified',failed_dataset=root/'failed')
                collector.assert_not_called()
            self.assertFalse((root/'verified').exists())
            failures=list((root/'failed').glob('*.json'))
            self.assertEqual(len(failures),1)
            data=json.loads(failures[0].read_text())
            self.assertIsNone(data['label'])
            self.assertEqual(data['failure_events'][0]['phase'],'before_unverified_move')


if __name__=='__main__':
    unittest.main()
