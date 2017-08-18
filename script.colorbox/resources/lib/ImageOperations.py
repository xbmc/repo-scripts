from PIL import ImageFilter
class MyGaussianBlur(ImageFilter.Filter):
    NAME = "GaussianBlur"
    def __init__(self, radius=10):
        self.radius = radius
    def filter(self, image):
        return image.gaussian_blur(self.radius)