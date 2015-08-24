import os, sys
from gi.repository import Gtk, GObject, Gdk
from pywinusb.window import AppWindow

def check_root_access():
    """ Sprwdzenie czy skrypt jest instalowany pod rootem
    :return: True jeśli root
    """
    return not os.geteuid()

def main():
    if not check_root_access():
        sys.exit("\nOnly root can run this script\n")

    win = AppWindow()
    win.show_all()

    Gdk.threads_enter()
    GObject.threads_init()
    Gtk.main()
    Gdk.threads_leave()

if __name__ == '__main__':
    sys.exit(main() or 0)