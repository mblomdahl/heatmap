# -*- coding: utf-8 -*-

import random

from PIL import Image

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import heatmap
from heatmap import colorschemes


class TestHeatmap(unittest.TestCase):
    """unittests for TestHeatmap"""

    def setUp(self):
        self.heatmap = heatmap.Heatmap()

    # TODO: Make test case remove created image on success, maybe?
    def test_heatmap_random_defaults(self):
        pts = [(random.random(), random.random()) for x in range(400)]
        img = self.heatmap.heatmap(pts)
        img.save("01-400-random.png")

        self.assertIsInstance(img, Image.Image)

    # TODO: Make test case remove created image on success, maybe?
    def test_heatmap_vert_line(self):
        pts = [(50, x) for x in range(100)]
        img = self.heatmap.heatmap(pts, area=((0, 0), (200, 200)))
        img.save("02-vert-line.png")

        self.assertIsInstance(img, Image.Image)

    # TODO: Make test case remove created image on success, maybe?
    def test_heatmap_horz_line(self):
        pts = [(x, 300) for x in range(600, 700)]
        img = self.heatmap.heatmap(
            pts, size=(800, 400), area=((0, 0), (800, 400)))
        img.save("03-horz-line.png")

        self.assertIsInstance(img, Image.Image)

    # TODO: Make test case remove created image on success, maybe?
    def test_heatmap_random(self):
        pts = [(random.random(), random.random()) for x in range(40000)]

        # This should also generate a warning on stderr of overly dense.
        img = self.heatmap.heatmap(pts, dotsize=25, opacity=128)
        img.save("04-40k-random.png")

        self.assertIsInstance(img, Image.Image)

    # TODO: Make test case remove created image on success, maybe?
    def test_heatmap_square(self):
        pts = [(x*100, 50) for x in range(2, 50)]
        pts.extend([(4850, x*100) for x in range(2, 50)])
        pts.extend([(x*100, 4850) for x in range(2, 50)])
        pts.extend([(50, x*100) for x in range(2, 50)])

        img = self.heatmap.heatmap(
            pts, dotsize=100, area=((0, 0), (5000, 5000)))
        img.save("05-square.png")

        self.assertIsInstance(img, Image.Image)

    # TODO: Make test case remove created image on success, maybe?
    def test_heatmap_single_point(self):
        pts = [(random.uniform(-77.012, -77.050),
                random.uniform(38.888, 38.910)) for x in range(100)]
        img = self.heatmap.heatmap(pts)
        self.heatmap.save_kml("06-wash-dc.kml")

        self.assertIsInstance(img, Image.Image)

    def test_invalid_heatmap(self):
        self.assertRaises(Exception, self.heatmap.heatmap, ([],))


class TestColorScheme(unittest.TestCase):

    def test_schemes(self):
        self.assertSetEqual(set(colorschemes.valid_schemes()),
                            {'fire', 'pgaitch', 'pbj', 'omg', 'classic'})

    def test_values(self):
        rgb_colors = range(256)

        for scheme, colors in colorschemes.SCHEMES.iteritems():
            self.assertIsInstance(colors, list)
            self.assertEqual(len(colors), 256)

            for color in colors:
                self.assertIsInstance(color, tuple)
                self.assertEqual(len(color), 3)

                red, green, blue = color

                self.assertIsInstance(red, int)
                self.assertIn(red, rgb_colors)

                self.assertIsInstance(green, int)
                self.assertIn(green, rgb_colors)

                self.assertIsInstance(blue, int)
                self.assertIn(blue, rgb_colors)


if __name__ == "__main__":
    unittest.main()
