from PIL import ImageFilter


class MyGaussianBlur(ImageFilter.Filter):
    NAME = "GaussianBlur"

    def __init__(self, radius=2):
        self.radius = radius

    def filter(self, image):
        return image.gaussian_blur(self.radius)


class UnsharpMask(ImageFilter.Filter):
    NAME = "UnsharpMask"

    def __init__(self, radius=2, percent=150, threshold=3):
        self.radius = 2
        self.percent = percent
        self.threshold = threshold

    def filter(self, image):
        return image.unsharp_mask(self.radius, self.percent, self.threshold)

