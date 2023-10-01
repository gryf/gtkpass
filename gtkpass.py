#!/usr/bin/env python
import signal

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib
from gi.repository import Gtk


class GTKPass(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="GTKPass")
        self.show_all()


def main():
    app = GTKPass()
    app.connect("delete-event", Gtk.main_quit)

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)
    Gtk.main()


if __name__ == '__main__':
    main()
