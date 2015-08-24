import threading, time

from gi.repository import Gtk, GObject, Gdk
from pywinusb.creator import USBCreator
from pywinusb.progress import ProgressWindow

# Okno aplikacji
class AppWindow(USBCreator, Gtk.Window):
    def __init__(self):
        super().__init__()
        Gtk.Window.__init__(self, title="pyWinUSB")

        self.set_border_width(10)
        self.set_size_request(150, -1)
        self.__create_wizard()
        self.connect("delete-event", Gtk.main_quit)

    def __create_wizard(self):
        """ Tworzenie kontrolek w oknie aplikacji
        """
        box = Gtk.Box(spacing=16)
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        box.pack_start(listbox, True, True, 0)
        self.add(box)

        # Ścieżka do obrazu
        row = Gtk.ListBoxRow()
        box = Gtk.HBox(spacing=8)

        row.add(box)
        box.pack_start(Gtk.Label("Image:"), False, False, 0)
        self.path = Gtk.Entry(xalign=0)
        box.pack_start(self.path, True, True, 0)

        open_button = Gtk.Button(stock=Gtk.STOCK_OPEN)
        open_button.connect("clicked", self.__show_file_chooser)
        box.pack_start(open_button, False, False, 0)

        listbox.add(row)

        # Dostępne urządzenia
        row = Gtk.ListBoxRow()
        box = Gtk.VBox(spacing=8)
        box.pack_start(Gtk.Label("Flash device:", xalign=0), True, False, 0)

        # Listowanie urządzeń co pół sekundy
        self.devices = Gtk.TreeView(Gtk.ListStore(str))
        self.devices.set_size_request(-1, 128)
        self.devices.append_column(Gtk.TreeViewColumn('', Gtk.CellRendererText(), text=0))
        self.devices.set_headers_visible(False)
        box.pack_start(self.devices, True, False, 0)

        row.add(box)
        listbox.add(row)

        # Podział
        listbox.add(Gtk.HSeparator())

        # Przyciski nawigacji
        row = Gtk.ListBoxRow()
        box = Gtk.HBox(spacing=4)
        box.pack_start( Gtk.LinkButton("http://www.github.com/Mati365", "Visit github repository", xalign=0)
                      , True, True, 0)

        apply = Gtk.Button(stock=Gtk.STOCK_APPLY)
        apply.connect("clicked", self.__create_boot_disc)
        box.pack_start(apply, True, True, 0)
        row.add(box)
        listbox.add(row)

        # Ładowanie listy urządzeń
        self.__load_device_list()

    def __create_boot_disc(self, button):
        """ Tworzenie bootowoalnego pendrive
        """
        path = self.path.get_text()
        if not path:
            raise Exception('Image path is empty')

        # Pobieranie z zaznaczenia
        (model, iter) = self.devices.get_selection().get_selected()
        if iter is None:
            raise Exception('Device is empty')

        # Pokazywanie okienka
        self.event_handler = ProgressWindow(self)
        self.event_handler.show_all()

        # Tworzenie dysku uruchomieniowego
        self.create_boot_disc(
              device=model[iter][0]
            , image_path=path
        )

    def __show_file_chooser(self, button):
        """ Tworzenie dialogu wyboru pliku obrazu
        """
        dialog = Gtk.FileChooserDialog("Please choose a file", self, Gtk.FileChooserAction.OPEN, (
              Gtk.STOCK_CANCEL
            , Gtk.ResponseType.CANCEL
            , Gtk.STOCK_OPEN
            , Gtk.ResponseType.OK
        ))

        filters = {
            "application/x-cd-image": "CD/DVD image"
        }
        for key, val in filters.items():
            filter_text = Gtk.FileFilter()
            filter_text.set_name(val)
            filter_text.add_mime_type(key)
            dialog.add_filter(filter_text)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.path.set_text(dialog.get_filename())
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")
        dialog.destroy()

    __cached_devices = []  # Urządzenia aktualnie widoczne w liście urządzeń
    def __load_device_list(self):
        """ Wczytywanie nowej listy urządzeń do listy
        co sekundę i kasowanie poprzedniej
        """
        def update_list():
            while True:
                # Wczytywanie nowej listy, jeśli znajdzie nowe urządzenie to wczytywanie od nowa
                new_devices = USBCreator.list_devices()
                if self.__cached_devices != new_devices:
                    self.__cached_devices = new_devices

                    # Wczytywanie nowych urządzeń do kontrolki
                    devices = self.devices.get_model()
                    devices.clear()

                    # Dodawanie urządzeń do listy
                    for mount_point in new_devices:
                        devices.append([ mount_point ])
                time.sleep(1)

        # Włączanie wątku odpowiedzialnego za odświeżanie urządzeń
        threading.Thread(target=update_list, daemon=True).start()