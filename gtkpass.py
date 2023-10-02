#!/usr/bin/env python
import os
import signal

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib
from gi.repository import Gtk
import yaml


XDG_CONF_DIR = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))


class GTKPass(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="GTKPass")

        self.passs = PassStore()
        self.passs.gather_pass_tree()
        self._border = 5
        self.make_ui()

    def make_ui(self):
        self.set_resizable(True)
        self.set_border_width(self._border)

        # main box
        mainbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                          spacing=self._border)
        mainbox.set_homogeneous(False)
        self.add(mainbox)

        # pane
        pane = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        mainbox.pack_start(child=pane, expand=True, fill=True, padding=0)

        # box for search entry
        lbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                       spacing=self._border)
        lbox.set_homogeneous(False)
        pane.pack1(child=lbox, resize=True, shrink=False)

        # search box
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Search password")
        lbox.pack_start(child=self.search, expand=False, fill=False, padding=0)

        self.show_all()


class Leaf:
    """A simple class to hold Leaf data"""
    def __init__(self, name, path):
        self.name = name
        self.path = path

    def __repr__(self):
        return f"Leaf: {self.name}"


class Tree:
    """A class to hold and manipulate leafs/other branches"""
    def __init__(self, name=None, path=None):
        self.name = name
        self.children = []
        self.path = path

    def __repr__(self):
        return f"Tree: {self.name}"

    @property
    def sorted_children(self):
        files = {}
        dirs = {}
        for i in self.children:
            if isinstance(i, Leaf):
                files[i.name] = i
            else:
                dirs[i.name] = i
        return ([dirs[x] for x in sorted(dirs)] +
                [files[x] for x in sorted(files)])


class PassStore:
    """Password store GUI app"""
    def __init__(self):
        self.store_path = self._get_store_path()
        self.data = Tree()
        self.conf = {}
        self._read_config()

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

    def _read_config(self):
        conf = os.path.join(XDG_CONF_DIR, 'gtkpass.yaml')

        try:
            with open(conf) as fobj:
                self.conf = yaml.safe_load(fobj)
        except OSError as e:
            print('Warning: There was an error on loading configuration '
                  'file:', e)
            pass


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
