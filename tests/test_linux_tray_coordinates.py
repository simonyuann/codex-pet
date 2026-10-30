"""StatusNotifier coordinates are native XWayland pixels, not Qt coordinates."""
import os
import sys
import unittest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from PyQt6.QtCore import QPoint, QRect
from codex_pet.linux_tray import native_to_qt


class Screen:
    def __init__(self, rect, scale):
        self.rect, self.scale = rect, scale
    def geometry(self):
        return self.rect
    def devicePixelRatio(self):
        return self.scale


class CoordinatesTest(unittest.TestCase):
    def test_scaled_second_screen_and_first_screen(self):
        screens = [Screen(QRect(2880, 0, 2560, 1440), 1.5),
                   Screen(QRect(0, 251, 1920, 1080), 1.5)]
        self.assertEqual(native_to_qt(5082, 48, screens), QPoint(4348, 32))
        self.assertEqual(native_to_qt(1200, 401, screens), QPoint(800, 351))

    def test_no_matching_screen(self):
        self.assertEqual(native_to_qt(-10, -20, []), QPoint(-10, -20))


if __name__ == '__main__':
    unittest.main()
