"""Linux tray click toggles the actual details panel in the app."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from PyQt6.QtCore import QPoint, QRect, QTimer
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from codex_pet.tray import QCursor
import codex_pet.__main__ as entry
from codex_pet.detail_panel import DetailPanel
from codex_pet.tray import Tray

class InspectTray(Tray):
    def __init__(self):
        super().__init__()
        QTimer.singleShot(0, self.check)

    def anchor_point(self):
        return QPoint(400, 23)

    def check(self):
        try:
            assert self.toggle_action is None
            with patch.object(self.icon, 'geometry', return_value=QRect(10, 0, 24, 24)), \
                 patch.object(QCursor, 'pos', return_value=QPoint(1200, 20)):
                assert Tray.anchor_point(self) == QPoint(1200, 20)
            with patch.object(self.icon, 'geometry', return_value=QRect(1190, 0, 24, 24)), \
                 patch.object(QCursor, 'pos', return_value=QPoint(1200, 20)):
                assert Tray.anchor_point(self) == QPoint(1201, 23)
            panel = next(w for w in QApplication.topLevelWidgets() if isinstance(w, DetailPanel))
            assert not panel.isVisible()
            self._on_activated(QSystemTrayIcon.ActivationReason.Trigger)
            assert panel.isVisible()
            screen = panel.screen() or QApplication.primaryScreen()
            available = screen.availableGeometry()
            assert panel.geometry().left() == 400
            assert panel.geometry().top() == 24
            panel.set_state({'active': 'deepseek', 'ds_status': 'online',
                             'deepseek': {'total': 1234567.89, 'currency': 'CNY'}})
            QApplication.processEvents()
            assert panel.geometry().left() == 400
            panel.set_state({'codex': {'plan_type': 'pro'}})
            assert panel.plan_label.text() == "ChatGPT Pro 配额"
            assert "Plus" not in panel.codex_header.text()
            self._on_activated(QSystemTrayIcon.ActivationReason.Trigger)
            assert not panel.isVisible()
            panel.popup_below_tray(QPoint(400, 599), QRect(0, 0, 800, 600))
            assert panel.geometry().bottom() < 599
            panel.hide_panel()
            print('Linux tray panel toggle: PASS')
        except BaseException as exc:
            print('Linux tray panel toggle: FAIL', repr(exc))
            os._exit(1)
        QApplication.quit()

with patch.object(entry, 'Tray', InspectTray), patch.object(entry.CodexClient, 'start'):
    raise SystemExit(entry.main())
