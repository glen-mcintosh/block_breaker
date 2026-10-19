import unittest
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from config import shape_classes
from screen_reader import load_profile, read_screen


def draw_block(draw, box, color):
    l,t,r,b = box
    adjust = lambda amount: tuple(max(0,min(255,int(value)+amount)) for value in color)
    draw.rectangle(box,fill=tuple(color))
    draw.rectangle((l,t,r,t+5),fill=adjust(50))
    draw.rectangle((l,b-5,r,b),fill=adjust(-50))
    draw.rectangle((l,t+6,l+5,b-6),fill=adjust(25))
    draw.rectangle((r-5,t+6,r,b-6),fill=adjust(-25))


class ScreenReaderTests(unittest.TestCase):
    def setUp(self):
        self.profile = load_profile()

    def screen(self, shape=None):
        image = Image.new('RGB', (450, 1000), (239, 166, 173))
        draw = ImageDraw.Draw(image)
        draw.rectangle(self.profile['board_box'], fill=tuple(self.profile['empty_rgb']))
        # A known occupied cell, bottom right.
        draw_block(draw,(377,594,422,639),self.profile['filled_rgb'])
        if shape:
            cells = shape_classes[shape]['shape']
            for r, row in enumerate(cells):
                for c, cell in enumerate(row):
                    if cell:
                        x,y=30+c*22,700+r*22
                        draw.rectangle((x,y,x+14,y+14),fill=tuple(self.profile['filled_rgb']))
        return image

    def test_every_catalog_shape(self):
        for name in shape_classes:
            with self.subTest(shape=name):
                state = read_screen(self.screen(name), self.profile)
                self.assertEqual(state.board, 1 << 63)
                self.assertEqual(state.pieces, (name, None, None))

    def test_blue_theme_palette(self):
        base = self.profile
        variant = base['variants'][0]
        for color in variant['filled_palette']:
            self.profile = {**base, **variant, 'filled_rgb': color}
            image = self.screen('ang_2_right_down')
            # Replace the synthetic pink background with the blue theme background.
            from PIL import ImageDraw
            ImageDraw.Draw(image).rectangle((0,850,449,999),fill=tuple(variant['background_rgb']))
            state = read_screen(image, base)
            self.assertEqual(state.pieces, ('ang_2_right_down',None,None))
            self.assertEqual(state.board,1 << 63)
        self.profile = base

    def test_new_color_is_recognized_without_palette(self):
        image = self.screen()
        ImageDraw.Draw(image).rectangle((30,700,45,715),fill='yellow')
        self.assertEqual(read_screen(image,self.profile).pieces,('zz_single',None,None))

    def test_empty_tray(self):
        self.assertEqual(read_screen(self.screen(), self.profile).pieces, (None, None, None))

    def test_block_interior_jitter_keeps_the_l_shape(self):
        image=self.screen()
        draw=ImageDraw.Draw(image)
        for row,y in enumerate((700,721,745)):
            for x in ((30,52) if row==0 else (30,)):
                draw.rectangle((x,y,x+14,y+14),fill=(210,220,230))
        self.assertEqual(read_screen(image,self.profile).pieces,('l_3',None,None))

    def test_single_tile_dither_does_not_select_its_shadow(self):
        from screen_reader import piece_geometry
        image=self.screen()
        draw=ImageDraw.Draw(image)
        l,t,r,b=self.profile['tray_boxes'][0]
        draw.rectangle((l,t,r-1,b-1),fill=(165,162,165))
        # A neutral shadow wins a single-bin histogram, but the two nearby
        # cyan interior colors together represent the actual tile.
        draw.rectangle((64,755,81,762),fill=(123,121,123))
        draw.rectangle((78,743,82,754),fill=(115,117,115))
        draw.rectangle((60,740,68,754),fill=(140,199,231))
        draw.rectangle((69,740,77,754),fill=(132,199,231))
        self.assertEqual(read_screen(image,self.profile).pieces,('zz_single',None,None))
        name,xs,ys=piece_geometry(image,self.profile,0)
        self.assertEqual(name,'zz_single')
        self.assertLessEqual(abs(float(np.mean(xs[0]))+15-68.5),1)
        self.assertLessEqual(abs(float(np.mean(ys[0]))+690-747),1)

    def test_blank_display_is_not_an_empty_game_board(self):
        with self.assertRaisesRegex(ValueError,'Screen is blank'):
            read_screen(Image.new('RGB',(450,1000),'black'),self.profile)

    def test_wrong_resolution(self):
        with self.assertRaisesRegex(ValueError, 'calibration expects'):
            read_screen(self.screen().resize((360,800)), self.profile)

    def test_overlay_on_board_rejected(self):
        image = self.screen()
        ImageDraw.Draw(image).rectangle((40,257,60,277),fill='white')
        with self.assertRaisesRegex(ValueError,'Ambiguous board cell'):
            read_screen(image,self.profile)

    def test_partial_piece_rejected(self):
        image = self.screen('line_3_h')
        ImageDraw.Draw(image).rectangle((30,700,36,714),fill=(239,166,173))
        with self.assertRaises(ValueError):
            read_screen(image,self.profile)

    def test_generated_themes_all_shapes_and_monochrome_blocks(self):
        themes = [((15,25,45),(40,45,60),(220,70,40)),
                  ((235,165,175),(120,60,70),(210,80,115)),
                  ((170,170,170),(68,72,68),(225,170,175)),
                  ((80,160,120),(25,55,45),(225,190,55)),
                  ((220,205,165),(95,85,50),(110,70,200)),
                  ((180,180,180),(65,65,65),(110,110,110))]
        for background,empty,block in themes:
            for name in shape_classes:
                with self.subTest(background=background,shape=name):
                    image=Image.new('RGB',(450,1000),background)
                    draw=ImageDraw.Draw(image)
                    draw.rectangle(self.profile['board_box'],fill=empty)
                    draw_block(draw,(27,244,72,289),block)
                    draw_block(draw,(377,594,422,639),block)
                    cells=shape_classes[name]['shape']
                    for r,row in enumerate(cells):
                        for c,cell in enumerate(row):
                            if cell:
                                x,y=30+c*22,700+r*22
                                draw.rectangle((x,y,x+14,y+14),fill=block)
                    state=read_screen(image,self.profile)
                    self.assertEqual(state.board,1 | (1<<63))
                    self.assertEqual(state.pieces,(name,None,None))

    def test_overlay_in_tray_rejected(self):
        image=self.screen()
        ImageDraw.Draw(image).rectangle((40,710,130,800),fill='white')
        with self.assertRaises(ValueError):
            read_screen(image,self.profile)

    def test_archived_screens_and_drag_coordinates(self):
        from game_player import plan_drag
        from solver import Move
        root=Path(__file__).resolve().parents[1]
        cases=json.loads((root/'tests/fixtures/screen_expectations.json').read_text())
        available=[case for case in cases if (root/case['path']).exists()]
        if not available:
            self.skipTest('Optional ignored gameplay screenshots are not available')
        for case in available:
            with self.subTest(path=case['path']):
                with Image.open(root/case['path']) as image:
                    actual=read_screen(image,self.profile)
                self.assertEqual(actual.board,int(case['board'],16))
                self.assertEqual(actual.pieces,tuple(case['pieces']))
        # Each logged drag has a known pickup/end position and a verified result.
        # Compare the new geometry to that calibration without sending any input.
        for log in (root/'captures').glob('session-*/moves.jsonl'):
            for record in map(json.loads,log.read_text().splitlines()):
                if record['status'] != 'verified':
                    continue
                before=Path(record['before_image']) if record.get('before_image') else log.parent/f"{record['step']:04d}-before.png"
                if not before.exists() or str(before.relative_to(root)) not in {case['path'] for case in cases}:
                    continue
                with Image.open(before) as image:
                    drag=plan_drag(image,self.profile,record['slot']-1,Move(**record['move']),pickup_index=record.get('pickup_index',0))
                for observed,expected in zip(drag.start+drag.end,tuple(record['drag']['start'])+tuple(record['drag']['end'])):
                    self.assertLessEqual(abs(observed-expected),3)


if __name__ == '__main__':
    unittest.main()
