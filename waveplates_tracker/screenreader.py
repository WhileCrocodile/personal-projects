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
        raise WindowNotExist("Could not find a running Wuthering Waves window.")
    # if win32gui.GetForegroundWindow() != hwnd:
    #     return None
    x, y, x1, y1 = win32gui.GetClientRect(hwnd)
    x, y = win32gui.ClientToScreen(hwnd, (x, y))
    x1, y1 = win32gui.ClientToScreen(hwnd, (x1 - x, y1 - y))
    im = pyautogui.screenshot(region=(x, y, x1, y1))
    return im


def template_match_waveplates(img: Image.Image, match_type="full") -> Image.Image | None:
    '''Uses template matching to detect the waveplate UI icon based on screenshot examples.'''
    templates = {
        "full": "templates/template_full.png",
        "blue": "templates/template_blue.png",
        "green": "templates/template_green.png",
    }

    img_cv2 = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2GRAY)  # convert to cv2
    if img_cv2.shape[1] != 1080:
        width, height = img_cv2.shape
        scale_factor = 1920 / height
        img_cv2 = cv2.resize(
            img_cv2, (1920, int(width * scale_factor)), interpolation=cv2.INTER_LINEAR
        )
    template = cv2.imread(templates[match_type], 0)

    width, height = template.shape[::-1]
    match_results = cv2.matchTemplate(img_cv2, template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.7
    loc = np.where(match_results >= threshold)
    if len(loc[0]) < 1:
        return None
    for pt in zip(*loc[::-1]):
        x, y = pt[0], pt[1]
        break  # If multiple x, y pairs found, only take the first
    
    left = (x) * (1/scale_factor)
    upper = (y) * (1/scale_factor)
    right = (x + width) * (1/scale_factor)
    lower = (y + height) * (1/scale_factor)
    return img.crop((left, upper, right, lower))


def crop_template_match(img: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Crop the image match returned from template_match_waveplates to only waveplate information (manual crop based on fixed template proportions)."""
    width, height = img.size
    upper = height * 0.1
    lower = height * 0.9

    green_left = width * 0.20
    green_right = width * 0.43

    blue_left = width * 0.60
    blue_right = width * 0.90

    green_crop = img.crop((green_left, upper, green_right, lower))
    blue_crop = img.crop((blue_left, upper, blue_right, lower))

    return (green_crop, blue_crop)

def fixed_crop_full_screenshot(img: Image.Image) -> Image.Image:
    """Crops a full-sized client window screenshot to only the top right portion containing the waveplate info.
    Used as a fallback method when waveplate detection fails."""
    width, _ = img.size
    left = width * 0.5  # left boundary in middle
    upper = 0  # upper boundary at max height
    right = width * 0.9  # crops out the map button on the right
    lower = width * 0.06  # crops to button size based on width
    return img.crop((left, upper, right, lower))

def crop_reduce_area(img: Image.Image) -> Image.Image:
    """Crops a full-sized client window screenshot to the top right quarter.
    Used in the first pass to reduce search area."""
    width, height = img.size
    left = width * 0.5  # left boundary in middle
    upper = 0  # upper boundary at max height
    right = width  # crops out the map button on the right
    lower = height * 0.5  # crops to button size based on width
    return img.crop((left, upper, right, lower))

def preprocess_img(img: Image.Image) -> Image.Image:
    """Image preprocessing to make OCR more accurate."""
    img = cv2.cvtColor(
        np.array(img), cv2.COLOR_BGR2GRAY
    )
    thresh = 200 # brightness value cutoff for conversion into black/white pixel 
    img = cv2.threshold(img, thresh, 255, cv2.THRESH_BINARY)[
        1
    ]  # convert to black and white
    # cv2.imshow(img_name, testimg)
    # cv2.waitKey()
    img = Image.fromarray(img).convert("RGB")
    return img


def waveplate_from_img(img: Image.Image) -> tuple[int, int]:
    """Read waveplate information from a full-window screenshot of the Wuthering Waves map.
    Returns a tuple in the format (blue_waveplates, green_waveplates).
    Returns a -1 in either entry if the text extraction fails."""

    # Regex text extraction function
    def extract(pattern: str, text: str):
        try:
            extracted = re.findall(pattern, text, flags=re.DOTALL)[0]
        except IndexError:
            extracted = -1
        return extracted

    # Image processing
    match = template_match_waveplates(crop_reduce_area(img)) # First try with reduced search area
    if match is None: # Second try with full image
        match = match = template_match_waveplates(img)

    if match is not None: # Main method using template matching to detect waveplates 
        img = match
        img = preprocess_img(img)
        green_img, blue_img = crop_template_match(img)
        green_ocr = pytesseract.image_to_string(green_img)
        blue_ocr = pytesseract.image_to_string(blue_img)
        green_waveplates = extract(r"\d{1,3}", green_ocr)
        blue_waveplates = extract(r"(\d{1,3})\/240", blue_ocr)
        return (int(blue_waveplates), int(green_waveplates))
    else: # Fallback method using a manual crop of the provided screenshot
        img = fixed_crop_full_screenshot(img)
        img = preprocess_img(img)
        # OCR
        ocr_text = pytesseract.image_to_string(img)
        # print(ocr_text)

        blue_waveplates = extract(r"(\d{1,3})\/240", ocr_text)
        green_waveplates = extract(r"30.+\s(\d{1,3})\s.+240", ocr_text)
        return (int(blue_waveplates), int(green_waveplates))
        


def waveplates_from_window(timeout: int = 15, retry_delay: int = 1) -> tuple[int, int]:
    """Gets waveplate information from an open Wuthering Waves window.
    Returns a tuple (blue_plates, green_plates)."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        img = screenshot_wuwa()
        # Failed to grab image, try again after delay
        if img is None:
            time.sleep(retry_delay)
            continue

        waveplates = waveplate_from_img(img)
        # OCR failed, try again after delay
        if waveplates[0] == -1 or waveplates[1] == -1:
            time.sleep(retry_delay)
            continue
        return waveplates  # Success
    raise TimeoutError("Operation timed out, could not get screenshot.")


def main():
    """For testing images."""
    screenshots_path = "screenshots/"
    imgs = []
    for i in range(1, 17):
        imgs.append(f"test{i}.png")
    for img_name in imgs:
        img_path = screenshots_path + img_name
        image = Image.open(img_path)
        # image = template_match_waveplates(image)

        # if image is None:
        #     print(f"Matching failed on {img_name}")
        # else:
        #     image.show()
        # green_img, blue_img = crop_template_match(image)
        # green_img = preprocess_img(green_img)
        # blue_img = preprocess_img(blue_img)
        # green_img.show()
        # blue_img.show()
        # print(pytesseract.image_to_string(green_img))
        # print(pytesseract.image_to_string(blue_img))
        # image = preprocess_img(image)
        # image.show()
        print(waveplate_from_img(image))

    # mystr = pytesseract.image_to_string("screenshots/test9_processed.png")
    # print(mystr)


if __name__ == "__main__":
    main()
