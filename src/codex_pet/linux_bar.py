"""Linux floating bar, anchored to the bottom right of the available screen."""

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication

from .status_bar import StatusBarBase


class LinuxBar(StatusBarBase):
    def _compute_base(self) -> QPoint:
        screen = self.screen() or QApplication.primaryScreen()
        geo = screen.availableGeometry()
        return QPoint(geo.right() - self.width() - 11,
                      geo.bottom() - self.height() - 11)

    def _apply_position(self) -> None:
        self.move(self._positioned(self._compute_base()))

    def _maintain(self) -> None:
        if self._drag_offset is None:
            self._apply_position()
