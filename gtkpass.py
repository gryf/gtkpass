#!/usr/bin/env python
import os
import signal

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
import yaml


XDG_CONF_DIR = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))


class GTKPass(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="GTKPass")

        self.passs = PassStore()
        self.passs.gather_pass_tree()
        self._border = 5
        self._expand = False
        self.make_ui()

    def make_ui(self):
        self.set_resizable(True)
        self.set_border_width(self._border)

        self.tree_store = Gtk.TreeStore(bool, str, Pango.Weight, str, str,
                                        bool)
        self.add_nodes(self.passs.data, None)

        # main box
        mainbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                          spacing=self._border)
        mainbox.set_homogeneous(False)
        self.add(mainbox)

        # pane
        pane = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        mainbox.pack_start(child=pane, expand=True, fill=True, padding=0)

        # box for search entry and treeview
        lbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                       spacing=self._border)
        lbox.set_homogeneous(False)
        pane.pack1(child=lbox, resize=True, shrink=False)

        # search box
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Search password")
        lbox.pack_start(child=self.search, expand=False, fill=False, padding=0)

        # treeview with filtering
        self.ts_filter = self.tree_store.filter_new()
        self.ts_filter.set_visible_column(0)
        self.treeview = Gtk.TreeView(model=self.ts_filter)
        self.treeview.set_headers_visible(False)

        icon_renderer = Gtk.CellRendererPixbuf()
        text_renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn()
        column.pack_start(icon_renderer, False)
        column.pack_start(text_renderer, False)
        column.add_attribute(text_renderer, "text", 1)
        column.add_attribute(text_renderer, "weight", 2)
        column.add_attribute(icon_renderer, "icon_name", 3)
        self.treeview.append_column(column)
        selection = self.treeview.get_selection()

        # scrollview to hold treeview
        tv_sw = Gtk.ScrolledWindow()
        tv_sw.add(self.treeview)
        lbox.pack_start(child=tv_sw, expand=True, fill=True, padding=0)

        self.show_all()
        self.refresh()
    def add_nodes(self, data, parent):
        "Create the tree nodes from a hierarchical data structure"
        for obj in data.sorted_children:
            if isinstance(obj, Tree):
                child = self.tree_store.append(parent,
                                               [True, obj.name,
                                                Pango.Weight.NORMAL,
                                                "folder",
                                                obj.path,
                                                False])
                self.add_nodes(obj, child)
            else:
                self.tree_store.append(parent, [True, obj.name,
                                                Pango.Weight.NORMAL,
                                                "application-x-generic",
                                                obj.path,
                                                True])

    def refresh(self, _widget=None):
        query = self.search.get_text().lower()
        if query == "":
            self.tree_store.foreach(self.reset_row, True)
            if self._expand:
                self.treeview.expand_all()
            else:
                self.treeview.collapse_all()
        else:
            self.tree_store.foreach(self.reset_row, False)
            self.tree_store.foreach(self.show_matches, query, True)
            self.treeview.expand_all()
        self.ts_filter.refilter()

    def reset_row(self, model, path, iter, make_visible):
        self.tree_store.set_value(iter, 2, Pango.Weight.NORMAL)
        self.tree_store.set_value(iter, 0, make_visible)


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
