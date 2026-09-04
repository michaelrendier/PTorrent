"""PTorrent — curses GUI.

LGPL-3.0-or-later. A native-curses face over ptorrent_core. Menu-driven shell;
each screen is its own module. First screen shipped: File ▸ New — the .ptorrent
wizard (ptorrent_gui.wizard).

Imports are kept lazy so sys.path can be arranged before ptorrent_core loads:

    from ptorrent_gui.shell import main
"""
__version__ = "1.0.0-dev"
