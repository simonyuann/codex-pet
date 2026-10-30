"""KDE StatusNotifierItem: preserve the coordinates supplied on activation."""
from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtCore import QObject, QPoint, pyqtClassInfo, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtDBus import QDBusConnection, QDBusInterface
from PyQt6.QtWidgets import QApplication


def native_to_qt(x: int, y: int, screens) -> QPoint:
    """Convert X11 native pixels to Qt's per-screen logical coordinates."""
    for screen in screens:
        geo, scale = screen.geometry(), screen.devicePixelRatio()
        if (geo.x() <= x < geo.x() + geo.width() * scale
                and geo.y() <= y < geo.y() + geo.height() * scale):
            return QPoint(geo.x() + round((x - geo.x()) / scale),
                          geo.y() + round((y - geo.y()) / scale))
    return QPoint(x, y)


@pyqtClassInfo('D-Bus Interface', 'org.kde.StatusNotifierItem')
class LinuxStatusNotifier(QObject):
    NewIcon = pyqtSignal()
    NewTitle = pyqtSignal()
    activated = pyqtSignal(QPoint)
    context = pyqtSignal(QPoint)

    def __init__(self, icon, parent=None):
        super().__init__(parent)
        self._dir = tempfile.TemporaryDirectory(prefix='codex-pet-tray-')
        self._icon_path = ''
        self._counter = 0
        self._title = 'Codex Pet'
        self.set_icon(icon)
        self._bus = QDBusConnection.sessionBus()
        self._path = '/CodexPetStatusNotifierItem'
        options = (QDBusConnection.RegisterOption.ExportAllSlots |
                   QDBusConnection.RegisterOption.ExportAllSignals |
                   QDBusConnection.RegisterOption.ExportAllProperties)
        if not self._bus.isConnected() or not self._bus.registerObject(self._path, self, options):
            raise RuntimeError('Cannot register StatusNotifierItem')
        watcher = QDBusInterface('org.kde.StatusNotifierWatcher', '/StatusNotifierWatcher',
                                 'org.kde.StatusNotifierWatcher', self._bus)
        if not watcher.isValid():
            self._bus.unregisterObject(self._path)
            raise RuntimeError('No StatusNotifier watcher')
        # The host may read properties while registering. Avoid a synchronous
        # call before Qt's event loop starts, which can deadlock both sides.
        watcher.asyncCall('RegisterStatusNotifierItem', self._path)

    @pyqtProperty(str)
    def Category(self): return 'ApplicationStatus'
    @pyqtProperty(str)
    def Id(self): return 'codex-pet'
    @pyqtProperty(str)
    def Title(self): return self._title
    @pyqtProperty(str)
    def Status(self): return 'Active'
    @pyqtProperty(str)
    def IconName(self): return self._icon_path
    @pyqtProperty(bool)
    def ItemIsMenu(self): return False

    @pyqtSlot(str)
    def ProvideXdgActivationToken(self, token):
        pass

    @pyqtSlot(int, int)
    def Activate(self, x, y):
        self.activated.emit(native_to_qt(x, y, QApplication.screens()))

    @pyqtSlot(int, int)
    def ContextMenu(self, x, y):
        self.context.emit(native_to_qt(x, y, QApplication.screens()))

    def set_icon(self, icon):
        self._counter += 1
        path = str(Path(self._dir.name) / f'icon-{self._counter}.png')
        icon.pixmap(64, 64).save(path, 'PNG')
        self._icon_path = path
        self.NewIcon.emit()

    def set_title(self, title):
        self._title = title
        self.NewTitle.emit()
