#!/usr/bin/env python
import os
import signal
import shutil
import subprocess

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import GLib  # noqa: E402
from gi.repository import Gdk  # noqa: E402
from gi.repository import Gtk  # noqa: E402
from gi.repository import Pango  # noqa: E402
import yaml  # noqa: E402


XDG_CONF_DIR = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))


class GTKPass(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="GTKPass")

        self.passs = PassStore()
        self.passs.gather_pass_tree()
        self.conf = self.passs.conf
        self._border = 5
        self._expand = False
        self._selected = None
        self.make_ui()

    def make_ui(self):
        if (self.conf.get('width') and self.conf.get('height')):
            self.resize(self.conf['width'], self.conf['height'])
        self.set_border_width(self._border)

        self.tree_store = Gtk.TreeStore(bool, str, Pango.Weight, str, str,
                                        bool)
        self.add_nodes(self.passs.data, None)

        # clipboard
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        # attach keyboard events
        self.connect("key-press-event", self.on_key_press_event)

        # main box
        mainbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                          spacing=self._border)
        mainbox.set_homogeneous(False)
        self.add(mainbox)

        # add toolbar
        toolbar = self.create_toolbar()
        mainbox.pack_start(child=toolbar, expand=False, fill=False, padding=0)

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
        self.search.connect("changed", self.refresh)
        lbox.pack_start(child=self.search, expand=False, fill=False, padding=0)

        # treeview with filtering
        self.ts_filter = self.tree_store.filter_new()
        self.ts_filter.set_visible_column(0)
        self.treeview = Gtk.TreeView(model=self.ts_filter)
        self.treeview.set_activate_on_single_click(True)
        self.treeview.set_headers_visible(False)
        self.treeview.connect("key-release-event", self.on_treeview_keypress)
        self.treeview.connect('row-activated', self.on_row_activated)

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
        selection.connect('changed', self.on_selected)

        # scrollview to hold treeview
        tv_sw = Gtk.ScrolledWindow()
        tv_sw.add(self.treeview)
        lbox.pack_start(child=tv_sw, expand=True, fill=True, padding=0)

        # display things
        rbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                       spacing=self._border)
        rbox.set_homogeneous(False)

        # entry preview
        self.grid = Gtk.Grid()
        self.grid.set_column_homogeneous(False)
        self.grid.set_row_homogeneous(False)
        self.grid.set_row_spacing(10)
        self.grid.set_column_spacing(10)

        self.label = Gtk.Label()
        self.label.set_use_markup(True)
        self.label.set_halign(Gtk.Align.START)

        self.grid.attach(self.label, 0, 0, 2, 1)
        for row, label in enumerate(['Username:', 'Password:',
                                     'URL:', 'Notes:'], start=1):
            label = Gtk.Label(label=label)
            label.set_halign(Gtk.Align.END)
            self.grid.attach(label, 0, row, 1, 1)

        sw = Gtk.ScrolledWindow()
        self.textview = Gtk.TextView()
        self.textview.set_editable(False)
        self.textview.set_hexpand(True)
        self.textview.set_vexpand(True)
        sw.add(self.textview)
        self.grid.attach(sw, 1, 4, 1, 1)
        self.user = Gtk.Entry()
        self.url = Gtk.Entry()
        self.password = Gtk.Entry()
        self.password.set_visibility(False)
        self.password.set_icon_from_icon_name(1, 'view-reveal-symbolic')
        self.password.set_icon_activatable(1, True)
        self.password.connect('icon-press', lambda obj, icon, ev:
                              obj.set_visibility(not obj.get_visibility()))
        for widget in (self.user, self.password, self.url):
            widget.set_editable(False)

        self.grid.attach(self.user, 1, 1, 1, 1)
        self.grid.attach(self.password, 1, 2, 1, 1)
        self.grid.attach(self.url, 1, 3, 1, 1)
        pane.pack2(child=self.grid, resize=True, shrink=False)

        # set split in ratio 40/60
        pane.set_position(int(4 * self.get_size()[0]/10))

        self.search.grab_focus()
        self.show_all()
        self._set_visible(self.grid, False)
        self.refresh()

    def _set_visible(self, obj, set_visible=True):
        for child in obj.get_children():
            if hasattr(child, 'get_children'):
                self._set_visible(child, set_visible)
            else:
                child.show() if set_visible else child.hide()
        self.textview.show() if set_visible else self.textview.hide()

    def create_toolbar(self):
        toolbar = Gtk.Toolbar()

        b_new = Gtk.ToolButton()
        b_new.set_icon_name("document-new-symbolic")
        toolbar.insert(b_new, 0)

        b_dir = Gtk.ToolButton()
        b_dir.set_icon_name("folder-new-symbolic")
        b_dir.connect("clicked", self.on_new_dir)
        toolbar.insert(b_dir, 1)

        b_edit = Gtk.ToolButton()
        b_edit.set_icon_name("document-edit-symbolic")
        toolbar.insert(b_edit, 2)

        b_del = Gtk.ToolButton()
        b_del.set_icon_name("edit-delete-symbolic")
        b_del.connect("clicked", self.on_delete)
        toolbar.insert(b_del, 3)

        b_gitpush = Gtk.ToolButton()
        b_gitpush.set_icon_name("go-up-symbolic")
        toolbar.insert(b_gitpush, 4)

        b_gitpull = Gtk.ToolButton()
        b_gitpull.set_icon_name("go-down-symbolic")
        toolbar.insert(b_gitpull, 5)

        return toolbar

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

    def make_path_visible(self, model, iter):
        while iter:
            self.tree_store.set_value(iter, 0, True)
            iter = model.iter_parent(iter)

    def make_subtree_visible(self, model, iter):
        for i in range(model.iter_n_children(iter)):
            subtree = model.iter_nth_child(iter, i)
            if model.get_value(subtree, 0):
                continue
            self.tree_store.set_value(subtree, 0, True)
            self.make_subtree_visible(model, subtree)

    def show_matches(self, model, path, iter, query,
                     show_subtrees_of_matches):
        text = model.get_value(iter, 1).lower()
        if query in text:
            # Highlight direct match with bold
            self.tree_store.set_value(iter, 2, Pango.Weight.BOLD)
            # Propagate visibility change up
            self.make_path_visible(model, iter)
            if show_subtrees_of_matches:
                # Propagate visibility change down
                self.make_subtree_visible(model, iter)
            return

    def on_row_activated(self, treeview, treepath, treeview_col):
        selection = treeview.get_selection()

        if not selection:
            return

        model, treeiter = selection.get_selected()

        if (self._selected is not None and
                self._selected == model[treeiter][4]):
            self._selected = None
            selection.unselect_all()
        else:
            self._selected = model[treeiter][4]

    def on_selected(self, selection):
        model, treeiter = selection.get_selected()

        self.label.set_label('')
        self.password.set_text('')
        self.user.set_text('')
        self.url.set_text('')
        self.textview.get_buffer().set_text('')

        if not (treeiter and model[treeiter] and model[treeiter][5]):
            self._set_visible(self.grid, False)
            return

        success, data = self.passs.get_pass(model[treeiter][4])
        if not success:
            self.label.set_label(f'<span foreground="red" size="x-large">'
                                 f'There is an error:\n{data}</span>')
            self.label.set_visible(True)
            return

        self.label.set_label(f'<span size="x-large">{model[treeiter][4]}'
                             f'</span>')
        output = data.split('\n')

        for count, line in enumerate(output):
            if count == 0:
                self.password.set_text(line.strip())
                continue
            if (output[count].lower().startswith('user:') or
                    output[count].lower().startswith('username:')):
                self.user.set_text(line.split(':')[1].strip())
                continue
            if output[count].lower().startswith('url:'):
                self.url.set_text(':'.join(line.split(':')[1:]).strip())
                continue
            if output[count].lower().startswith('notes:'):
                self.textview.get_buffer().set_text("\n".join(output[count:])
                                                    [6:].strip())
                break
        self._set_visible(self.grid, True)

    def on_treeview_keypress(self, treeview, event):
        # expand current branch on right cursor key or enter/return
        if (event.keyval in (Gdk.KEY_Right, Gdk.KEY_Return) and
                treeview.get_cursor()[0]):
            treeview.expand_row(treeview.get_cursor()[0], False)
        # collapse row under cursor on left cursor key
        if event.keyval == Gdk.KEY_Left and treeview.get_cursor()[0]:
            treeview.collapse_row(treeview.get_cursor()[0])

    def on_new_dir(self, button):
        if self._selected is None:
            path = ''
        else:
            path = self._selected

        dialog = NewDirDialog(self, path)
        response = dialog.run()
        dirname = dialog.get_dirname()
        dialog.destroy()

        if response != Gtk.ResponseType.OK or not dirname:
            return

        result, msg = self.passs.new_dir(os.path.join(path, dirname))
        if not result:
            dialog = Gtk.MessageDialog(transient_for=self,
                                       flags=0,
                                       message_type=Gtk.MessageType.INFO,
                                       buttons=Gtk.ButtonsType.CLOSE,
                                       text='There was an error')

            dialog.format_secondary_text(msg)
            dialog.run()
            dialog.destroy()

        selection = self.treeview.get_selection()
        if not selection:
            return
        tree_model_filter, tree_paths = selection.get_selected_rows()
        tree_store = tree_model_filter.get_model()
        tree_iter = None
        if tree_paths:
            tree_iter = tree_store.get_iter(tree_paths[0])

        self.tree_store.append(tree_iter, [True, dirname,
                                           Pango.Weight.NORMAL, "folder",
                                           os.path.join(path, dirname), False])

    def on_delete(self, button):
        if not self._selected:
            return

        # TODO: add configurable confirmation?
        result, msg = self.passs.delete(self._selected)
        if result == self.passs.NON_EMPTY:
            dialog = Gtk.MessageDialog(transient_for=self,
                                       flags=0,
                                       message_type=Gtk.MessageType.QUESTION,
                                       buttons=Gtk.ButtonsType.OK_CANCEL,
                                       text='Directory not empty')
            dialog.format_secondary_text(f'Do you want to delete '
                                         f'{self._selected} recursively?')
            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.OK:
                result, msg = self.passs.delete(self._selected, True)

        if result == self.passs.ERROR:
            dialog = Gtk.MessageDialog(transient_for=self,
                                       flags=0,
                                       message_type=Gtk.MessageType.INFO,
                                       buttons=Gtk.ButtonsType.CLOSE,
                                       text='There was an error')
            dialog.format_secondary_text(msg)
            dialog.run()
            dialog.destroy()
        self._selected = None

        # remove selected branch/leaf from store
        selection = self.treeview.get_selection()
        tree_model_filter, tree_paths = selection.get_selected_rows()
        tree_store = tree_model_filter.get_model()

        for path in tree_paths:
            tree_iter = tree_store.get_iter(path)
            tree_store.remove(tree_iter)

    def on_key_press_event(self, widget, event):
        ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)
        if ctrl and event.keyval == Gdk.KEY_b:
            if self.user.get_text != '':
                self.clipboard.set_text(self.user.get_text(), -1)
        elif ctrl and event.keyval == Gdk.KEY_c:
            if self.password.get_text != '':
                self.clipboard.set_text(self.password.get_text(), -1)
        # TODO: clear clipboard after a minute or so.


class NewDirDialog(Gtk.Dialog):
    def __init__(self, parent, path):
        super().__init__(title="Enter new directory", transient_for=parent,
                         flags=0)
        self.set_modal(True)
        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_OK, Gtk.ResponseType.OK)

        label = Gtk.Label(label=f"Create new directory under "
                          f"{'/' if not path else path} path")

        box = self.get_content_area()
        box.add(label)
        self.entry = Gtk.Entry()
        self.entry.connect("key-release-event", self.on_release_key)
        box.add(self.entry)
        self.show_all()

    def on_release_key(self, entry, event):
        if event.keyval == Gdk.KEY_Return:
            self.response(Gtk.ResponseType.OK)

    def get_dirname(self):
        return self.entry.get_text()


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
    NON_EMPTY = 1
    SUCCESS = 0
    ERROR = 2

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
        self.data = Tree()
        self._gather_pass_tree(self.data, self.store_path, '')

    def get_pass(self, path):
        proc = subprocess.run(['pass', path], capture_output=True,
                              encoding='utf-8')
        if proc.returncode == 0:
            return True, proc.stdout
        else:
            return False, proc.stderr

    def new_dir(self, dirname):
        path = os.path.join(self.store_path, dirname)
        try:
            os.mkdir(os.path.join('/root', path), mode=500)
            return True, ''
        except IOError as exc:
            return False, str(exc)

    def delete(self, item, recursively=False):
        path = os.path.join(self.store_path, item)

        if os.path.exists(path) and os.path.isdir(path) and recursively:
            try:
                shutil.rmtree(path)
            except IOError as exc:
                return self.ERROR, str(exc)
        elif os.path.exists(path) and os.path.isdir(path):
            _, files, dirs = next(os.walk(path))
            if files or dirs:
                return self.NON_EMPTY, ""
            try:
                shutil.rmtree(path)
            except IOError as exc:
                return self.ERROR, str(exc)
        elif not os.path.exists and os.path.isfile(path + '.gpg'):
            try:
                os.unlink(path + '.gpg')
            except IOError as exc:
                return self.ERROR, str(exc)

        return self.SUCCESS, ''

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

    def write_config(self):
        conf = os.path.join(XDG_CONF_DIR, 'gtkpass.yaml')

        try:
            with open(conf, 'w') as fobj:
                yaml.safe_dump(self.conf, fobj)
        except OSError as e:
            print('Warning: There was an error on loading configuration '
                  'file:', e)
            pass


def _check_pass_store(path):
    if not os.path.exists(path) or not os.path.isdir(path):
        raise IOError("Path for password store `%s' either doesn't exists or "
                      "is not a directory", path)


def quit(app, event):
    if app.conf.get('save_dimension'):
        dim = app.get_size()
        app.conf['width'] = dim.width
        app.conf['height'] = dim.height
        app.passs.write_config()
    Gtk.main_quit(app, event)


def main():
    app = GTKPass()
    app.connect("delete-event", quit)

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, quit)
    Gtk.main()


if __name__ == '__main__':
    main()
