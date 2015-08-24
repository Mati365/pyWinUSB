import sh, os, re, threading, hashlib, subprocess
from gi.repository import Gtk

from pywinusb.decorators import chain_method, event_method
from pywinusb.events import EventHandler

# Dialog potwierdzenia
def MessageBox(parent, title, message, buttons=Gtk.ButtonsType.OK_CANCEL, type=Gtk.MessageType.WARNING):
    dialog = Gtk.MessageDialog(parent, 0, type, buttons, title)
    dialog.format_secondary_text(message)
    response = dialog.run()
    dialog.destroy()
    return response

# Klasa kreatora dysku
class USBCreator:
    def __init__(self, event_handler = EventHandler()):
        self.source_mount = None
        self.destination_mount = None
        self.copy_thread = None
        self.event_handler = event_handler

    @staticmethod
    def list_devices():
        """ Listowanie wszystkich punktów montowania wszystkich pendrive
        :return: Lista urządzeń
        """
        mount_points = []
        popen = os.popen("grep -lir '1' /sys/block/sd*/removable")
        for block_device in iter(popen.readline, ""):
            mount_points.append("/dev/{}".format(re.search("(\w*)\/removable$", block_device).group(1)))
        return mount_points

    @staticmethod
    def get_mount_path(device):
        """ Pobieranie ścieżki, w której zamontowane jest urządzenie
        :param device: Urządzenie np. /dev/sdb
        """
        for line in sh.mount():
            match = re.search("^{}.*on.(.*) type".format(device), line)
            if match is not None:
                return match.group(1)

    @chain_method
    @event_method("Opening device...")
    def open_device(self):
        self.device_size = int(sh.blockdev("--getsize64", self.device)) # Rozmiar w MB

        # Odmontowywanie urządzenia jeśli jest ono zamontowane
        mount_path = USBCreator.get_mount_path(self.device)
        if mount_path:
            response = MessageBox( parent=self
                                 , title="Device is already in use"
                                 , message="Unmount device {device} mounted in:\n {mount_path}?"
                                    .format(device=self.device, mount_path=mount_path)
                                 )
            if response == Gtk.ResponseType.OK:
                # Odmontowywanie urządzenia jeśli zatwierdzone
                sh.umount(mount_path)
            else:
                raise Exception("Device must be unmounted before copying!")

    @chain_method
    @event_method("Erasing device...")
    def erase_device(self):
        """ Wymazywanie całego urządzenia
        """
        # Tworzenie nowej tablicy partycji
        subprocess.call(["parted", self.device, "mklabel", "msdos", "--script"])
        subprocess.call(["parted", self.device, "mkpart", "primary", "ntfs", "0%", "100%"])

        # Formatowanie na NTFSa
        subprocess.call(["mkfs.ntfs", "-Q", self.device + "1"])

    @chain_method
    @event_method("Mounting devices...")
    def mount_devices(self):
        """ Montowanie obrazu dysku
        :param image_path: Ścieżka bezwzględna do obrazu
        """
        if os.path.getsize(self.image_path) > self.device_size:
            raise Exception("Image is too big!")

        self.mount_folder = "/media/pyWinUSB/{}".format(hashlib.sha1(self.image_path.encode("utf-8")).hexdigest())
        self.source_mount = self.mount_folder  + "/source"
        self.destination_mount = self.mount_folder  + "/destination"

        # Montownie obrazu ISO dysku
        sh.mkdir(self.source_mount, self.destination_mount, "-p")
        sh.mount(self.image_path, self.source_mount, o="loop")

        # Montowanie urządzenia
        subprocess.call(["sfdisk", self.device, "-R"])
        subprocess.call(["mount", self.device + "1", self.destination_mount])

    @chain_method
    @event_method("Copying files...")
    def copy_files(self):
        # Pliki do skopiowania
        files_to_copy = []
        for root, dirnames, filenames in os.walk(self.source_mount):
            for file in filenames:
                files_to_copy.append(root + '/' + file)

        # Modyfikacja ścieżki oraz kopiowanie plików
        for index, file in enumerate(files_to_copy):
            match = re.search("pyWinUSB\/\w{40}\/source\/(.*\/)", file)
            dest_file = "/".join([
                  self.destination_mount
                , match.group(1) if match else ""
            ])

            # Tworzenie i kopiowanie
            self.event_handler.on_progress(len(files_to_copy), index, file)
            sh.mkdir(dest_file, "-p")
            sh.cp(file, dest_file)

    @chain_method
    @event_method("Installing GRUB...")
    def make_bootable(self):
        """ Tworzenie dysku bootowalnego
        """
        self.uuid = re.search("UUID=\"(\w*)\"", str(sh.blkid(self.device + "1"))).group(1)
        print("Device UUID:", self.uuid)

        # W niektórych wersjach windows katalog ten jest z drukowanej
        self.boot_folder = self.destination_mount + "/boot"
        try: sh.mv(self.destination_mount + "/BOOT", self.boot_folder)
        except:
            pass

        # Instalownie bootloadera
        # grub-install --target=i386-pc --boot-directory="/<USB_mount_folder>/boot" /dev/sdX
        installer = sh.Command("grub-install")
        installer(self.device, target="i386-pc", boot_directory=self.destination_mount + "/boot")

        # Tworzenie konfiguracji GRUBa
        with open("{}/grub/grub.cfg".format(self.boot_folder), "wt") as config:
            config.write("""
                set menu_color_normal=white/black
                set menu_color_highlight=black/light-gray
                menuentry 'Install Windows' {
                    ntldr /bootmgr
                }
            """)

    @chain_method
    @event_method("Umount devices...")
    def close_stream(self):
        """ Zamykanie urządzenia i kasowanie plików tymczasowych
        """
        if self.source_mount is not None:
            sh.sync()
            sh.umount(self.source_mount, self.destination_mount)
            sh.rm(self.mount_folder, '-rf')

    def create_boot_disc(self, device, image_path):
        """ Tworzenie dysku instalacyjnego na pendrive
        :param device:      Urządzenie np. /dev/sdb
        :param image_path:  Ścieżka do surowego obrazu
        """
        self.device = device
        self.image_path = image_path

        # Instalacja w innym wątku by nie wieszać UI
        try:
            self \
                .open_device() \
                .erase_device() \
                .mount_devices()
        except:
            self\
                .close_stream()\
                .event_handler.on_done(True)

        finally:
            def worker():
                self \
                    .copy_files() \
                    .make_bootable() \
                    .close_stream() \
                    .event_handler.on_done()

            # Wątek kopiowania
            self.copy_thread = threading.Thread(target=worker, daemon=True)
            self.copy_thread.start()

    def stop_copying(self):
        """ Zatrzymywania kopiowania plików np. po zamknięciu dialogu
        """
        self.close_stream()
        if self.copy_thread is not None:
            self.copy_thread.quit()