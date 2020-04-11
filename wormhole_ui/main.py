import logging
import sys

from PySide2 import QtCore, QtGui
from PySide2.QtWidgets import QApplication
import qt5reactor
import twisted.internet

from .util import get_icon_path

# Fix for pyinstaller packages app to avoid ReactorAlreadyInstalledError
# See https://github.com/kivy/kivy/issues/4182 and
# https://github.com/pyinstaller/pyinstaller/issues/3390
if "twisted.internet.reactor" in sys.modules:
    del sys.modules["twisted.internet.reactor"]

# Importing readline (in the wormhole dependency) after initialising QApplication
# causes segfault in Ubuntu. Importing it here to workaround this.
try:
    import readline  # noqa: F401, E402
except ImportError:
    pass

QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
QApplication([])
qt5reactor.install()

from .widgets.main_window import MainWindow  # noqa: E402
from .protocol import WormholeProtocol  # noqa: E402


def run():
    logging.basicConfig(level=logging.INFO)
    QApplication.setWindowIcon(QtGui.QIcon(get_icon_path()))

    reactor = twisted.internet.reactor
    wormhole = WormholeProtocol(reactor)
    main_window = MainWindow(wormhole)
    main_window.run()

    sys.exit(reactor.run())
