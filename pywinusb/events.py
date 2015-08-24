# Klasa odpowiedzialna za eventy
class EventHandler:
    def on_progress(self, total, current, file):
        """ Metoda wywoływana podczas kopiowania pliku
        :param total:   Liczba wszystkich plików
        :param current: Aktualny index pliku
        :param file:    Plik
        :return:
        """
        pass

    def on_status(self, status):
        """ Metoda wywoływna podczas zmiany statusu
        :param status: Informacja na statusbar
        :return:
        """
        pass

    def on_done(self, err):
        """ Metoda wywoływana po skończeniu kopiowania
        :param err: True jeśli błąd
        """
        pass