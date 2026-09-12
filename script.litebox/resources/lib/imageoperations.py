from PIL import ImageFilter, Image
import random, math
class MyGaussianBlur(ImageFilter.GaussianBlur):
    NAME = "GaussianBlur"
    def __init__(self, radius=10):
        super().__init__(radius)