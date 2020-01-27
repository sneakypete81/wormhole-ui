import logging
import sys

from PySide2 import QtCore
from PySide2.QtWidgets import QApplication
import qt5reactor
import twisted.internet


# fix for pyinstaller packages app to avoid ReactorAlreadyInstalledError
# See https://github.com/kivy/kivy/issues/4182 and
# https://github.com/pyinstaller/pyinstaller/issues/3390
if "twisted.internet.reactor" in sys.modules:
    del sys.modules["twisted.internet.reactor"]

QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
QApplication([])
qt5reactor.install()

from .widgets.main_window import MainWindow  # noqa: E402
from .wormhole_controller import WormholeController  # noqa: E402


def run():
    logging.basicConfig(level=logging.INFO)

    reactor = twisted.internet.reactor
    wormhole = WormholeController(reactor)
    main_window = MainWindow(wormhole)
    main_window.run()

    sys.exit(reactor.run())
