import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import ImageDraw

from game_player import Drag,HeldPreviewError,inspect_held,send_drag,wait_stable
from screen_reader import ScreenState
from test_verified_collection import frames,tile


def held_frame(before, profile, aligned=True, lifted=True):
    held=before.copy()
    draw=ImageDraw.Draw(held)
    if lifted:
        l,t,r,b=profile['tray_boxes'][0]
        draw.rectangle((l,t,r-1,b-1),fill=(239,166,173))
    if aligned:
        tile(draw,(27,244,72,289),(239,97,140))
    return held


class HeldPreviewTests(unittest.TestCase):
    def test_requires_lifted_piece_and_interior_at_target(self):
        p,im1,im2,before,after,move=frames()
        self.assertTrue(inspect_held(im1,held_frame(im1,p),p,0,move)['approved'])
        self.assertFalse(inspect_held(im1,held_frame(im1,p,aligned=False),p,0,move)['approved'])
        self.assertFalse(inspect_held(im1,held_frame(im1,p,lifted=False),p,0,move)['approved'])
        self.assertFalse(inspect_held(im1,im1,p,0,move)['approved'])

    def test_approved_preview_is_saved_before_release(self):
        p,im1,im2,before,after,move=frames()
        with tempfile.TemporaryDirectory() as folder,patch('game_player._gesture') as gesture:
            path=Path(folder)/'held.png'
            result=send_drag('test',Drag((67,747),(67,510)),before_image=im1,profile=p,slot=0,
                             move=move,capture=lambda:held_frame(im1,p),preview_path=path)
            self.assertTrue(result['approved'])
            self.assertTrue(path.exists())
            self.assertTrue(json.loads(path.with_suffix('.json').read_text())['approved'])
            self.assertEqual(len(gesture.call_args_list),2)
            self.assertFalse(any(' UP ' in c for c in gesture.call_args_list[0].args[1]))
            self.assertIn(' UP 67 510',gesture.call_args_list[1].args[1][0])

    def test_rejected_preview_cancels_below_board_and_never_releases_at_target(self):
        p,im1,im2,before,after,move=frames()
        with tempfile.TemporaryDirectory() as folder,patch('game_player._gesture') as gesture:
            with self.assertRaises(HeldPreviewError):
                send_drag('test',Drag((67,747),(67,510)),before_image=im1,profile=p,slot=0,
                          move=move,capture=lambda:im1,preview_path=Path(folder)/'held.png')
            commands=[c for call in gesture.call_args_list for c in call.args[1]]
            self.assertNotIn('input touchscreen motionevent UP 67 510',commands)
            self.assertIn('input touchscreen motionevent UP 67 920',commands)

    def test_capture_failure_or_interrupt_cancels_and_propagates(self):
        p,im1,im2,before,after,move=frames()
        for error in (OSError('lost ADB'),KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__),tempfile.TemporaryDirectory() as folder,patch('game_player._gesture') as gesture:
                with self.assertRaises(type(error)):
                    send_drag('test',Drag((67,747),(67,510)),before_image=im1,profile=p,slot=0,
                              move=move,capture=lambda:(_ for _ in ()).throw(error),preview_path=Path(folder)/'held.png')
                self.assertIn('input touchscreen motionevent UP 67 920',gesture.call_args_list[-1].args[1])


class UnchangedTests(unittest.TestCase):
    def test_unchanged_requires_full_observation_window_and_two_matches(self):
        p,im1,im2,before,after,move=frames()
        with patch('game_player.read_screen',return_value=before),patch('game_player.time.monotonic',side_effect=[0,1,2,10]),patch('game_player.time.sleep'):
            image,state=wait_stable(lambda:im1,p,timeout=5,expected_board=after.board,before=before,
                                    slot=0,allow_unchanged=True)
        self.assertEqual(state,before)

    def test_changed_or_unreadable_observation_prevents_retry_even_if_board_returns(self):
        p,im1,im2,before,after,move=frames()
        for first in (ScreenState(2,before.pieces),ValueError('unclear frame')):
            with self.subTest(first=first),patch('game_player.read_screen',side_effect=[first,before,before]),patch('game_player.time.monotonic',side_effect=[0,1,2,3,10]),patch('game_player.time.sleep'):
                with self.assertRaisesRegex(ValueError,'Stopped waiting'):
                    wait_stable(lambda:im1,p,timeout=5,expected_board=after.board,before=before,
                                slot=0,allow_unchanged=True)

    def test_one_unchanged_observation_is_insufficient(self):
        p,im1,im2,before,after,move=frames()
        with patch('game_player.read_screen',return_value=before),patch('game_player.time.monotonic',side_effect=[0,1,10]),patch('game_player.time.sleep'):
            with self.assertRaises(ValueError):
                wait_stable(lambda:im1,p,timeout=5,expected_board=after.board,before=before,slot=0,allow_unchanged=True)


class RetryLoopTests(unittest.TestCase):
    def run_player(self, observations, *, retries=1, drag_error=None):
        from live import play
        p,im1,im2,before,after,move=frames()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch('live.wait_stable',side_effect=observations),patch('live.best_moves',return_value=SimpleNamespace(moves=[move],elapsed_ms=0)),patch('live.plan_drag',return_value=Drag((1,1),(2,2))) as plan,patch('live.send_drag',side_effect=drag_error) as send,patch('live.capture',side_effect=OSError('offline')),contextlib.redirect_stdout(io.StringIO()):
                error=None
                try:
                    play('test',p,root,root/'raw',1,failed_dataset=root/'failed',drag_retries=retries)
                except ValueError as caught:
                    error=caught
                records=[json.loads(line) for line in next(root.glob('session-*/moves.jsonl')).read_text().splitlines()]
                return error,send.call_count,plan.call_args_list,records

    def test_unchanged_attempt_retries_once_then_verifies(self):
        p,im1,im2,before,after,move=frames()
        error,count,plans,records=self.run_player([(im1,before),(im1,before),(im1,before),(im1,before),(im2,after)])
        self.assertIsNone(error)
        self.assertEqual(count,2)
        self.assertEqual([call.kwargs['pickup_index'] for call in plans],[0,1])
        self.assertEqual(records[-1]['status'],'verified')
        self.assertEqual(records[-1]['attempt'],2)

    def test_preview_rejection_can_retry_only_after_unchanged_confirmation(self):
        p,im1,im2,before,after,move=frames()
        error,count,_,_=self.run_player([(im1,before),(im1,before),(im1,before),(im1,before),(im2,after)],drag_error=[HeldPreviewError('missed pickup'),None])
        self.assertIsNone(error)
        self.assertEqual(count,2)

    def test_retry_limit_is_enforced(self):
        p,im1,im2,before,after,move=frames()
        error,count,_,_=self.run_player([(im1,before)]*5)
        self.assertIsNotNone(error)
        self.assertEqual(count,2)

    def test_changed_preflight_or_uncertain_result_prevents_second_drag(self):
        p,im1,im2,before,after,move=frames()
        for observations in ([(im1,before),(im1,before),ValueError('unexpected board')],
                             [(im1,before),(im1,before),(im1,before),(im2,after)]):
            error,count,_,_=self.run_player(observations)
            self.assertIsNotNone(error)
            self.assertEqual(count,1)

    def test_zero_retry_option_stops_after_first_unchanged_attempt(self):
        p,im1,im2,before,after,move=frames()
        error,count,_,_=self.run_player([(im1,before)]*3,retries=0)
        self.assertIsNotNone(error)
        self.assertEqual(count,1)


if __name__=='__main__':
    unittest.main()
