"""Class for getting and storing info about waveplate progression."""

import time
import math
import json

WAVEPLATE_REGEN_TIME = 360  # seconds per waveplate
MAX_BLUE_PLATES = 240
MAX_GREEN_PLATES = 480
BLUE_TO_GREEN_RATE = 0.5

# class PlayerInfo():
#     def __init__(self, name=None):
#         self.name = name
#
#     def export_info():
#       pass

# class GameEvent:
#     def __init__(self, name=None, rewards=None):
#         self.name = name
#         self.rewards = dict() if rewards==None else rewards


class WaveplateTracker:
    """Class for saving and retrieving waveplate information."""

    DEFAULT_FILE_PATH = "waveplate_history.txt"

    @staticmethod
    def make_plate_property(plate_type: str):
        """Temporary function to define getter/setter methods for each plate type."""
        plate_name = "_" + plate_type + "_plates"

        @property
        def prop(self):
            return getattr(self, plate_name)

        @prop.setter
        def prop(self, value):
            setattr(self, "last_update_time", time.time())
            setattr(self, plate_name, int(value))

        return prop

    blue_plates = make_plate_property("blue")
    green_plates = make_plate_property("green")

    def __init__(
        self,
        blue_plates: int = 0,
        green_plates: int = 0,
        last_update_time: int = 0,
        file_path: str = "",
    ):
        self.blue_plates = blue_plates
        self.green_plates = green_plates
        self.last_update_time = last_update_time
        self.last_update_time = (
            time.time() if last_update_time == 0 else last_update_time
        )
        self.file_path = self.DEFAULT_FILE_PATH if file_path == "" else file_path

    @classmethod
    def from_json(cls, file_path: str = ""):
        """Creates a WaveplateTracker object by loading history from json."""
        if file_path == "":
            file_path = cls.DEFAULT_FILE_PATH
        with open(file_path, mode="r", encoding="utf-8") as file:
            data = json.loads(file.read())
        return cls(
            blue_plates=data["blue_plates"],
            green_plates=data["green_plates"],
            last_update_time=data["last_update_time"],
        )

    def to_json(self, file_path: str = ""):
        """Exports current data to JSON file."""
        if file_path == "":
            file_path = self.file_path
        with open(file_path, mode="w", encoding="utf-8") as file:
            data = self.as_dict()
            json.dump(data, file)

    def get_plate_info(self):
        """Calculates and returns the current waveplate info from saved history."""
        current_time = time.time()
        time_diff = current_time - self.last_update_time
        new_plates = math.floor(time_diff / WAVEPLATE_REGEN_TIME)
        current_blue_plates = self.blue_plates + new_plates
        current_green_plates = self.green_plates

        if current_blue_plates > MAX_BLUE_PLATES:
            overflow_plates = current_blue_plates - MAX_BLUE_PLATES
            current_green_plates = current_green_plates + (
                overflow_plates * BLUE_TO_GREEN_RATE
            )
            current_green_plates = math.floor(current_green_plates)
            current_blue_plates = MAX_BLUE_PLATES

        time_to_full = (
            (MAX_BLUE_PLATES - current_blue_plates) * WAVEPLATE_REGEN_TIME / 3600
        )
        return {
            "blue_plates": current_blue_plates,
            "green_plates": current_green_plates,
            "time_to_full": time_to_full,
        }

    def update_plates_prompt(self):
        """
        Prompt the model to ask for waveplates in the terminal.
        True if successfully completed or cancelled, False if input was invalid.
        """
        new_data = input(
            "Please enter your waveplates in the format blue_plates/green_plates (e.g. 60/255), otherwise type cancel.\n"
        )
        if new_data == "cancel":
            return True
        try:
            new_data = new_data.split("/")
            for idx, num in enumerate(new_data):
                new_data[idx] = int(num.strip())
            self.blue_plates = new_data[0]
            self.green_plates = new_data[1]
            self.to_json()
            print("Waveplates updated.\n")
            return True
        except ValueError:
            print("Invalid format.\n")
            return False
        except IndexError:
            print("Did not provide enough values.\n")

    def get_plate_message(self):
        """Returns results from WaveplateTracker.get_plate_info() as a string message."""
        results = self.get_plate_info()
        message = f"You have {results["blue_plates"]} blue plates, {results["green_plates"]} green plates, and {results["time_to_full"]} hours until full.\n"
        return message

    def as_dict(self):
        """Returns waveplate history data as a dictionary."""
        return {
            "blue_plates": self.blue_plates,
            "green_plates": self.green_plates,
            "last_update_time": self.last_update_time,
        }

    def __repr__(self):
        return str(self.as_dict())


def main():
    running = True
    actions = {"1": "check", "2": "update", "3": "exit"}
    while running:
        try:
            command = input("What would you like to do? (1)check (2)update (3)exit\n")
            command = actions[command]
            if command == "check":
                plate_tracker = WaveplateTracker.from_json()
                message = plate_tracker.get_plate_message()
                print(message)
            elif command == "update":
                plate_tracker = WaveplateTracker.from_json()
                success = plate_tracker.update_plates_prompt()
                while not success:
                    success = plate_tracker.update_plates_prompt()
            elif command == "exit":
                running = False
        except:
            print("Unrecognized command.")
    # Update plates
    # plate_tracker = WaveplateTracker.from_json()
    # plate_tracker.blue_plates = 38
    # plate_tracker.to_json()

    # Check plates
    plate_tracker = WaveplateTracker.from_json()


if __name__ == "__main__":
    main()
