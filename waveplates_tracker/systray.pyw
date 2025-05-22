"""System tray icon for displaying waveplate progression."""

import time
import threading
from PIL import Image
import pystray
import win32ui
from win32con import MB_SYSTEMMODAL
import platetracker as ptrack
import screenreader

# class IconEditableText():
#     def __init__(self, icon: pystray.Icon, text: str):
#         super().__init__()
#         self.icon = icon
#         self.text = text

#     def __get__(self, obj, objtype=None):
#         return getattr(self, "text")

#     def __set__(self, obj, value):
#         setattr(self, "text", value)
#         self.icon.update_menu()

#     def __str__(self):
#         return self.text


class WaveplateIcon(pystray.Icon):
    """System tray program for using and updating information in WaveplateTracker."""

    @property
    def screenreader_status(self):
        """Text for the "update from window" button. Calls icon.update_menu() when set."""
        return self._screenreader_status

    @screenreader_status.setter
    def screenreader_status(self, value):
        self._screenreader_status = value
        self.update_menu()

    def __init__(self, plate_tracker: ptrack.WaveplateTracker | None = None):
        self.reader_thread = None
        ICON_IMAGE = Image.open("assets/Item_Waveplate.webp")
        self.program_name = "waveplate_tracker"
        self.plate_tracker = (
            ptrack.WaveplateTracker.from_json()
            if plate_tracker is None
            else plate_tracker
        )
        self._screenreader_status = "Click to load waveplates from window."
        super().__init__(
            self.program_name,
            ICON_IMAGE,
            "Waveplate Tracker",
            menu=pystray.Menu(*self.create_menu_items(self.plate_tracker)),
        )
        self.update_menu_periodic()

    def create_menu_items(
        self, plate_tracker: ptrack.WaveplateTracker
    ) -> tuple[pystray.MenuItem, ...]:
        """Make items for the pystray menu."""

        def plate_callback(
            info_key: str, left_message: str = "", right_message: str = ""
        ):
            """Returns a callback function to update the text in menu items."""

            def inner(icon):
                return (
                    left_message
                    + str(plate_tracker.get_plate_info()[info_key])
                    + right_message
                )

            return inner

        def update_plates_manual(icon, item):
            # plate_tracker.update_plates_prompt()
            pass

        blue_item = pystray.MenuItem(
            plate_callback("blue_plates", "Daily plates: "),
            lambda icon: icon.update_menu(),
        )
        green_item = pystray.MenuItem(
            plate_callback("green_plates", "Overflow plates: "),
            lambda icon: icon.update_menu(),
        )
        time_item = pystray.MenuItem(
            plate_callback("time_to_full", "Time to full: ", " hours"),
            lambda icon: icon.update_menu(),
        )
        automatic_update_item = pystray.MenuItem(
            lambda x: self.screenreader_status, self.update_plates_from_window
        )
        # manual_update_item = pystray.MenuItem("Click to update waveplates manually.", update_plates_manual)
        exit_item = pystray.MenuItem("Quit", action=lambda icon: icon.stop())
        return (
            blue_item,
            green_item,
            time_item,
            pystray.Menu.SEPARATOR,
            automatic_update_item,
            pystray.Menu.SEPARATOR,
            exit_item,
        )

    def update_plates_from_window(self):
        """Updates the waveplate count by reading them from the Wuthering Waves map interface."""

        def inner():
            self.screenreader_status = (
                "Waiting for waveplates... (open and stay on the map)"
            )
            try:
                plates = screenreader.waveplates_from_window()
            except screenreader.WindowNotExist:
                self.screenreader_status = "Click to update waveplates from window."
                return win32ui.MessageBox(
                    "Could not find the Wuthering Waves window.",
                    f"{self.name}: Error",
                    MB_SYSTEMMODAL,
                )
            except TimeoutError:
                self.screenreader_status = "Click to update waveplates from window."
                return win32ui.MessageBox(
                    "Operation timed out, failed to read waveplates from window.",
                    f"{self.name}: Error",
                    MB_SYSTEMMODAL,
                )
            # print(plates)
            self.plate_tracker.blue_plates, self.plate_tracker.green_plates = (
                plates[0],
                plates[1],
            )
            self.plate_tracker.to_json()
            win32ui.MessageBox(
                "Waveplates successfully updated!",
                f"{self.name}: Success",
                MB_SYSTEMMODAL,
            )
            self.screenreader_status = "Click to update waveplates from window."

        if (
            self.reader_thread is None or not self.reader_thread.is_alive()
        ):  # Only make thread if no previous thread is active
            self.reader_thread = threading.Thread(daemon=True, target=inner)
            self.reader_thread.start()

    def update_menu_periodic(self):
        """Spawns a thread that periodically re-updates the menu text."""

        def inner():
            running = True
            while running:
                time.sleep(ptrack.WAVEPLATE_REGEN_TIME)
                self.update_menu()

        threading.Thread(daemon=True, target=inner).start()

    def empty_action(self, icon, item):
        """A do-nothing function to pass to menu items which only display text."""


def main():
    '''Create and run the system tray icon.'''
    icon = WaveplateIcon()
    icon.run_detached()


if __name__ == "__main__":
    main()
