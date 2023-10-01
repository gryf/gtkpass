#!/usr/bin/env python
import signal

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib
from gi.repository import Gtk


class GTKPass(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="GTKPass")

        self.passs = PassStore()
        self.passs.gather_pass_tree()
    def make_ui(self):
        self.show_all()


class PassStore:
    """Password store GUI app"""
    def __init__(self):
        self.store_path = self._get_store_path()
        self.data = Tree()
        self.conf = {}

    def _get_store_path(self):
        path = os.environ.get('$PASSWORD_STORE_DIR')
        if path:
            _check_pass_store(path)
            return path

        path = os.path.expanduser('~/.password-store')
        _check_pass_store(path)
        return path

    def gather_pass_tree(self):
        self._gather_pass_tree(self.data, self.store_path, '')

    def _gather_pass_tree(self, model, root, dirname):
        fullpath = os.path.join(root, dirname)
        ps_path = fullpath[len(self.store_path)+1:]

        root, dirs, files = next(os.walk(fullpath))
        for fname in files:
            if (fname in ['.gitattributes', '.gpg-id'] or
                    not fname.lower().endswith('.gpg')):
                continue
            fname = fname[:-4]  # chop off extension
            model.children.append(Leaf(fname, os.path.join(ps_path, fname)))

        for dname in dirs:
            if dname == '.git':
                continue
            t = Tree(dname, os.path.join(ps_path, dname))
            model.children.append(t)
            self._gather_pass_tree(t, root, dname)



def _check_pass_store(path):
    if not os.path.exists(path) or not os.path.isdir(path):
        raise IOError("Path for password store `%s' either doesn't exists or "
                      "is not a directory", path)


def main():
    app = GTKPass()
    app.connect("delete-event", Gtk.main_quit)

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)
    Gtk.main()


if __name__ == '__main__':
    main()
