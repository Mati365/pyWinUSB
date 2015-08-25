import sh, os, re, threading, hashlib, subprocess
from gi.repository import Gtk

from pywinusb.decorators import chain_method, event_method
from pywinusb.events import EventHandler
from pywinusb.decorators import installer_method

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

        self.format_filesystem = "ntfs"
        self.format_table = "msdos"

    @staticmethod
    def get_filesystem_name(device, partition=1):
        """
        :param device:      Urządzenie
        :param partition:   Numer partycji
        :return: System plików na partycji
        """
        return re.search("\n\w*.(\w*)", str(sh.lsblk(device + str(partition), fs=True))).group(1)

    @staticmethod
    def get_device_size(device, whole_device=False):
        """ Pobieranie rozmiarów urządzenia/partycji
        :param already_formatted: Czy jest właśnie sformatowany
        :return: Rozmiar w bajtach
        """
        try:
            if not whole_device:
                # Sprawdzanie systemu plików, jeśli nie jest to NTFS to wysypuje się
                return int(re.search("\n\/dev\/(?:\w*\s*){3}(\d*)", str(sh.df(device + "1"))).group(1)) * 1024

            # Pobieranie rozmiaru całego urządzenia
            return int(sh.blockdev("--getsize64", device))
        except:
            return -1

    @staticmethod
    def list_devices():
        """ Listowanie wszystkich punktów montowania wszystkich pendrive
        :return: Lista urządzeń
        """
        mount_points = []
        popen = os.popen("grep -lir '1' /sys/block/sd*/removable")
        for block_device in iter(popen.readline, ""):
            device = "/dev/{}".format(re.search("(\w*)\/removable$", block_device).group(1))
            mount_points.append([device, USBCreator.get_device_size(device, True)])
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

    @installer_method("Opening device...")
    def open_device(self):
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

    @installer_method("Erasing device...")
    def erase_device(self):
        """ Wymazywanie całego urządzenia
        """
        # Tworzenie nowej tablicy partycji
        subprocess.call(["parted", self.device, "mklabel", "msdos", "--script"])
        subprocess.call(["parted", self.device, "mkpart", "primary", "ntfs", "0%", "100%"])

        # Formatowanie na NTFSa
        subprocess.call(["mkfs.ntfs", "-Q", self.device + "1"])

    @installer_method("Mounting devices...")
    def mount_devices(self):
        """ Montowanie obrazu dysku
        :param image_path: Ścieżka bezwzględna do obrazu
        """
        self.mount_folder = "/media/pyWinUSB/{}".format(hashlib.sha1(self.image_path.encode("utf-8")).hexdigest())
        self.source_mount = self.mount_folder  + "/source"
        self.destination_mount = self.mount_folder  + "/destination"

        # Odmontowywanie na wszelki wypadek
        try: sh.umount(self.source_mount)
        except:
            pass

        # Montownie obrazu ISO dysku
        sh.mkdir(self.source_mount, self.destination_mount, "-p")
        sh.mount(self.image_path, self.source_mount, o="loop")

        # Montowanie urządzenia
        subprocess.call(["sfdisk", self.device, "-R"])
        subprocess.call(["mount", self.device + "1", self.destination_mount])

        # Sprawdzanie systemu plików pod kątem rozmiaru
        if USBCreator.get_device_size(self.device) < os.path.getsize(self.image_path):
            raise Exception("No enough space on disk/partition!")

        # Sprawdzenie typu systemu plików
        # elif USBCreator.get_filesystem_name(self.device) != "ntfs":
        #     raise Exception("Unsupported filesystem!")


    @installer_method("Copying files...")
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

    @installer_method("Installing GRUB...")
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

    @installer_method("Umount devices...")
    def close_stream(self):
        """ Zamykanie urządzenia i kasowanie plików tymczasowych
        """
        if self.source_mount is not None:
            sh.sync()
            sh.umount(self.source_mount, self.destination_mount)
            sh.rm(self.mount_folder, '-rf')

    def create_boot_disc(self, device, image_path, format_device=False):
        """ Tworzenie dysku instalacyjnego na pendrive
        :param device:      Urządzenie np. /dev/sdb
        :param image_path:  Ścieżka do surowego obrazu
        """
        self.device = device
        self.image_path = image_path

        # Instalacja w innym wątku by nie wieszać UI
        try:
            err_title = None
            self.open_device()
            if format_device:
                self.erase_device()
            self.mount_devices()

            # Wątek kopiowania
            def worker():
                self \
                    .copy_files() \
                    .make_bootable() \
                    .close_stream() \
                    .event_handler.on_done()
            self.copy_thread = threading.Thread(target=worker, daemon=True)
            self.copy_thread.start()

        # Po złapaniu błędu wyświetlany jest warning i odmontowywane urządzenia
        except Exception as err:
            err_title = err.args[0]
        except:
            print(os.sys.exc_info())
            err_title = os.sys.exc_info()[0]
        finally:
            if err_title is not None:
                self\
                    .close_stream()\
                    .event_handler.on_done(err_title)

    def stop_copying(self):
        """ Zatrzymywania kopiowania plików np. po zamknięciu dialogu
        """
        self.close_stream()
        if self.copy_thread is not None:
            self.copy_thread.quit()