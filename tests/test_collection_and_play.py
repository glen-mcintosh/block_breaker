import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from config import shape_classes
from game_player import expected_tray, plan_drag, wait_stable
from screen_reader import ScreenState, load_profile
from shape_capture import save_shapes
from solver import Move


class CollectionTests(unittest.TestCase):
    def test_crops_are_unlabelled_deduplicated_and_empty_slots_skipped(self):
        profile=load_profile()
        image=Image.new('RGB',(450,1000),'purple')
        ImageDraw.Draw(image).rectangle(profile['tray_boxes'][2],fill='green')
        state=ScreenState(0,('square_2',None,'t_up'))
        with tempfile.TemporaryDirectory() as folder:
            saved=save_shapes(image,profile,state,folder)
            self.assertEqual(len(saved),2)
            with Image.open(saved[0]) as crop:
                self.assertEqual(crop.size,(135,130))
            data=json.loads(saved[0].with_suffix('.json').read_text())
            self.assertIsNone(data['label'])
            self.assertEqual(data['predicted_shape'],'square_2')
            self.assertEqual(data['slot'],1)
            self.assertEqual(save_shapes(image,profile,state,folder),[])
            draw=ImageDraw.Draw(image)
            draw.point((20,700),fill='white')
            self.assertEqual(len(save_shapes(image,profile,state,folder)),1)
            # Unknown observations are saved without predicted labels.
            more=save_shapes(image,profile,None,folder)
            self.assertTrue(more)
            self.assertIsNone(json.loads(more[0].with_suffix('.json').read_text())['predicted_shape'])


class PlayTests(unittest.TestCase):
    def test_remaining_pieces_must_stay_in_their_slots(self):
        before=ScreenState(0,('zz_single','square_2','t_up'))
        self.assertTrue(expected_tray(before,ScreenState(1,(None,'square_2','t_up')),0))
        self.assertFalse(expected_tray(before,ScreenState(1,(None,'t_up','square_2')),0))
        last=ScreenState(0,(None,'square_2',None))
        self.assertFalse(expected_tray(last,ScreenState(1,(None,None,None)),1))
        self.assertTrue(expected_tray(last,ScreenState(1,('t_up','square_2','zz_single')),1))

    def test_drag_plan_uses_actual_piece_center_and_calibration(self):
        profile=load_profile()
        image=Image.new('RGB',(450,1000),(239,166,173))
        draw=ImageDraw.Draw(image)
        draw.rectangle(profile['board_box'],fill=tuple(profile['empty_rgb']))
        # Left corner with occupied-cell centers at (82,745),(104,745),(82,767).
        for x,y in ((75,738),(97,738),(75,760)):
            draw.rectangle((x,y,x+14,y+14),fill=tuple(profile['filled_rgb']))
        move=Move(0,'ang_2_right_down',0,0,0)
        drag=plan_drag(image,profile,0,move)
        self.assertEqual(drag.start,(82,745))
        self.assertEqual(drag.end,(70,509))
        for name in shape_classes:
            # Fixtures in screen-reader tests exercise recognition for the whole catalog.
            # Here verify that uncalibrated input is never sent.
            with self.assertRaisesRegex(ValueError,'calibration'):
                plan_drag(image,{**profile,'drag':{}},0,Move(0,name,0,0,0))

    def test_waits_for_two_matching_expected_observations(self):
        before=ScreenState(0,('zz_single','square_2',None))
        expected=ScreenState(1,(None,'square_2',None))
        wrong=ScreenState(2,(None,'square_2',None))
        observations=iter([before,wrong,expected,expected])
        image=Image.new('RGB',(1,1))
        with patch('game_player.read_screen',side_effect=lambda *args:next(observations)),patch('game_player.time.sleep'):
            _,actual=wait_stable(lambda:image,{},expected_board=1,before=before,slot=0)
        self.assertEqual(actual,expected)

    def test_failure_log_preserves_recognition_reason_without_sending_input(self):
        from live import play
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)
            with patch('live.wait_stable',side_effect=ValueError('Tray slot 3: bad grid')),patch('live.capture',side_effect=OSError('offline')),patch('live.send_drag') as send:
                with self.assertRaisesRegex(ValueError,'Tray slot 3'):
                    play('test',load_profile(),output,output/'data',1)
                send.assert_not_called()
            failure=json.loads(next(output.glob('session-*/failure.json')).read_text())
            self.assertEqual(failure['error'],'Tray slot 3: bad grid')
            self.assertIsNone(failure['last_move'])

    def test_mismatch_times_out_and_never_advances(self):
        image=Image.new('RGB',(1,1))
        before=ScreenState(0,('zz_single','square_2',None))
        with patch('game_player.read_screen',return_value=before),patch('game_player.time.sleep'),patch('game_player.time.monotonic',side_effect=[0,1,2,10]):
            with self.assertRaisesRegex(ValueError,'expected move result'):
                wait_stable(lambda:image,{},timeout=5,expected_board=1,before=before,slot=0)


if __name__=='__main__':
    unittest.main()
