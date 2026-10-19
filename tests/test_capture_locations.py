import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from unittest.mock import patch

from shape_capture import (DEFAULT_DATASET,DEFAULT_FAILED_DATASET,DEFAULT_VERIFIED_DATASET,
                           save_failed_shapes)
from test_verified_collection import frames


class CaptureLocationTests(unittest.TestCase):
    def test_defaults_use_existing_capture_and_training_trees(self):
        root=Path(__file__).resolve().parents[1]
        self.assertEqual(DEFAULT_DATASET,root/'captures/unclassified')
        self.assertEqual(DEFAULT_FAILED_DATASET,root/'captures/failed_shapes')
        self.assertEqual(DEFAULT_VERIFIED_DATASET,root/'shape_model/shapes')

    def test_failed_piece_stays_unlabelled_and_context_is_preserved(self):
        profile,im1,im2,before,after,move=frames()
        with tempfile.TemporaryDirectory() as folder:
            paths=save_failed_shapes(im1,profile,folder,state=before,slots=[0],
                                     error='bad placement',session='session-test',phase='before_unverified_move')
            self.assertEqual(len(paths),1)
            data=json.loads(paths[0].with_suffix('.json').read_text())
            self.assertIsNone(data['label'])
            self.assertEqual(data['predicted_shape'],'zz_single')
            self.assertEqual(data['failure_events'][0]['error'],'bad placement')
            self.assertEqual(save_failed_shapes(im1,profile,folder,state=before,slots=[0],
                                                error='second attempt',session='session-test'),[])
            data=json.loads(paths[0].with_suffix('.json').read_text())
            self.assertEqual(len(data['failure_events']),2)

    def test_error_slot_limits_crops_and_empty_slots_are_skipped(self):
        profile,im1,im2,before,after,move=frames()
        with tempfile.TemporaryDirectory() as folder:
            paths=save_failed_shapes(im1,profile,folder,error='Tray slot 2: bad mask')
            self.assertEqual(len(paths),1)
            self.assertEqual(json.loads(paths[0].with_suffix('.json').read_text())['slot'],2)
            self.assertEqual(save_failed_shapes(im1,profile,folder,error='Tray slot 3: bad mask'),[])

    def test_unreadable_slot_is_saved_but_blank_display_is_not(self):
        profile,im1,im2,before,after,move=frames()
        with tempfile.TemporaryDirectory() as folder:
            with patch('screen_reader.read_screen',side_effect=ValueError('bad mask')),patch('screen_reader.piece_geometry',side_effect=ValueError('bad mask')):
                paths=save_failed_shapes(im1,profile,folder,error='Tray slot 1: bad mask')
            self.assertEqual(len(paths),1)
            data=json.loads(paths[0].with_suffix('.json').read_text())
            self.assertIsNone(data['predicted_shape'])
            self.assertEqual(save_failed_shapes(Image.new('RGB',(450,1000),'black'),profile,folder),[])
            self.assertEqual(save_failed_shapes(Image.new('RGB',(100,100),'red'),profile,folder),[])


if __name__=='__main__':
    unittest.main()
