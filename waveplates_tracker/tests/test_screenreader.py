import pytest
import json
from PIL import Image
import os
from context import screenreader as sreader

def test_images():
    '''Test the screenreader functionality on a collection of screenshots.'''
    path = "./screenshots/"
    a_path = os.path.join(path, "annotations.json")
    with open(a_path, mode="r", encoding="utf-8") as file:
        annotations = json.load(file)
    for img_name, data in annotations.items():
        img_path = os.path.join(path, img_name)
        img = Image.open(img_path)
        plates = sreader.waveplate_from_img(img)
        assert plates==tuple(data), f"Failed to read {img_name}, expected {tuple(data)} but instead got {plates}."