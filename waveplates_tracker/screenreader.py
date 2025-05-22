"""Script to get full-window screenshots from Wuthering Waves and read waveplate information."""

import time
import re
import numpy as np
from PIL import Image
import cv2
import pytesseract
import pyautogui
import win32gui


pytesseract.pytesseract.tesseract_cmd = r".\tesseract\tesseract.exe"


class WindowNotExist(Exception):
    """Raise this exception when the window cannot be found."""


def screenshot_wuwa() -> Image.Image:
    """Returns a screenshot of the Wuthering Waves window. Requires the window to exist."""

    hwnd = win32gui.FindWindow(
        None, "Wuthering Waves  "
    )  # Lagging spaces are not a mistake
    if not hwnd:
        raise WindowNotExist("Couldn't find Wuthering Waves.")
    # if win32gui.GetForegroundWindow() != hwnd:
    #     return None
    x, y, x1, y1 = win32gui.GetClientRect(hwnd)
    x, y = win32gui.ClientToScreen(hwnd, (x, y))
    x1, y1 = win32gui.ClientToScreen(hwnd, (x1 - x, y1 - y))
    im = pyautogui.screenshot(region=(x, y, x1, y1))
    return im


def crop_to_waveplates(file_path: str) -> Image.Image:
    """Crops a full-sized image to only the top right portion containing the waveplate info."""
    img = Image.open(file_path)
    width, _ = img.size
    left = width * 0.5  # left boundary in middle
    upper = 0  # upper boundary at max height
    right = width * 0.9  # crops out the map button on the right
    lower = width * 0.06  # crops to button size based on width
    return img.crop((left, upper, right, lower))


def waveplate_from_img(img: Image.Image) -> tuple[int, int]:
    """Read waveplate information from a full-window screenshot of the Wuthering Waves map.
    Returns a tuple in the format (blue_waveplates, green_waveplates).
    Returns a -1 in either entry if the text extraction fails."""
    # Image processing
    img = cv2.cvtColor(
        np.array(img), cv2.COLOR_BGR2GRAY
    )  # convert to cv2 to apply filters
    thresh = 200
    img = cv2.threshold(img, thresh, 255, cv2.THRESH_BINARY)[
        1
    ]  # convert to black and white
    # cv2.imshow(img_name, testimg)
    # cv2.waitKey()
    img = Image.fromarray(img).convert("RGB")  # back to PIL Image to feed into OCR

    # OCR
    ocr_text = pytesseract.image_to_string(img)

    # Regex text extraction
    def extract(pattern: str, text: str):
        try:
            text = re.findall(pattern, text)[0]
        except IndexError:
            text = -1
        return text

    blue_waveplates = extract(r"(\d{1,3})\/240", ocr_text)
    green_waveplates = extract(r"30.+\s(\d{1,3})\s.+240", ocr_text)
    return (blue_waveplates, green_waveplates)


def waveplates_from_window(timeout: int = 15, delay: int = 1) -> tuple[int, int]:
    """Gets waveplate information from an open Wuthering Waves window.
    Returns a tuple (blue_plates, green_plates)."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        img = screenshot_wuwa()
        if img is None:  # Failed to grab image, try again after delay
            time.sleep(delay)
            continue
        waveplates = waveplate_from_img(img)
        if (
            waveplates[0] == -1 or waveplates[1] == -1
        ):  # OCR failed, try again after delay
            time.sleep(delay)
            continue
        return waveplates  # Success
    raise TimeoutError("Operation timed out, could not get screenshot.")


def main():
    print(waveplates_from_window())


if __name__ == "__main__":
    main()
