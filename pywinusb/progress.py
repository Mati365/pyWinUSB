import re

from gi.repository import Gtk, GObject
from pywinusb.events import EventHandler
from pywinusb.creator import MessageBox

# Okno kopiowania plików
class ProgressWindow(Gtk.Window, EventHandler):
    def __init__(self, creator):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL, title="File copying")

        self.creator = creator

        self.connect("delete-event", lambda *args, **kwargs: True)
        self.connect("destroy-event", lambda *args, **kwargs: True)

        self.set_border_width(10)
        self.set_size_request(400, -1)
        self.set_modal(True)

        self.__create_window()

    def __create_window(self):
        box = Gtk.VBox(spacing=8)
        self.add(box)

        # Pasek postępu
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        box.pack_start(self.progress_bar, True, True, 0)

        # Pasek statusu
        self.status_bar = Gtk.Statusbar()
        self.status_context = self.status_bar.get_context_id("Status")
        box.pack_start(self.status_bar, True, True, 0)

    def update_progress(self, file, percent):
        """ Aktualizacja paska procentu
        :param file:    Plik
        :param percent: Procent
        """
        self.progress_bar.set_fraction(percent)
        self.progress_bar.set_text("File: {file} - {percent}%".format(file=file, percent=int(percent * 100)))

    def update_status(self, status):
        """ Aktualizacja pasku statusu
        :param status: Treść statusu
        """
        self.status_bar.push(self.status_context, status)

    def show_warning(self, title, content, type=Gtk.MessageType.INFO):
        """
        :param title:   Tytuł
        :param content: Treść
        :return:
        """
        MessageBox(self.creator, title, content, Gtk.ButtonsType.OK, type)

    # Callbacki z innego wątku
    def on_status(self, status):
        GObject.idle_add(self.update_status, status)
    def on_progress(self, total, current, file):
        GObject.idle_add( self.update_progress
                        , re.search("pyWinUSB\/\w{40}\/source\/(.*)", file).group(1)
                        , current / total
                        )
    def on_done(self, err=False):
        if err:
            GObject.idle_add(self.show_warning, "Error!", "Check logs!", Gtk.MessageType.WARNING)
        else:
            GObject.idle_add(self.show_warning, "Copying done!", "You can eject device!")
        self.destroy()