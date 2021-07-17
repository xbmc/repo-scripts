"""
Created on Sep. 25, 2019

Based on ScreenBloom by Tyler Kershner
https://github.com/kershner/screenBloom
http://www.screenbloom.com/


"""
#import os
#import time
#import xbmc

from PIL import ImageEnhance
from resources.lib import timer


class ImageProcess(object):

    def __init__(self):

        self.LOW_THRESHOLD = 10
        self.MID_THRESHOLD = 30
        self.HIGH_THRESHOLD = 240


    @timer
    def img_avg(self,img,minBri,maxBri,saturation):
        dark_pixels = 1
        mid_range_pixels = 1
        total_pixels = 1
        r = 1
        g = 1
        b = 1
    
        if saturation > 1.0:
            sat_converter = ImageEnhance.Color(img)
            img = sat_converter.enhance(saturation)

        #=======================================================================
        #clock = time.localtime()
        #savepath = os.path.join(xbmc.translatePath("special://userdata/addon_data/script.service.hue/capture/"), str(clock) + ".png")
        #img.save(savepath)
        #=======================================================================


        # Create list of pixels
        pixels = list(img.getdata())

        for red, green, blue, alpha in pixels:
            # Don't count pixels that are too dark
            if red < self.LOW_THRESHOLD and green < self.LOW_THRESHOLD and blue < self.LOW_THRESHOLD:
                dark_pixels += 1
            # Or too light
            elif red > self.HIGH_THRESHOLD and green > self.HIGH_THRESHOLD and blue > self.HIGH_THRESHOLD:
                pass
            else:
                if red < self.MID_THRESHOLD and green < self.MID_THRESHOLD and blue < self.MID_THRESHOLD:
                    mid_range_pixels += 1
                    dark_pixels += 1
                r += red
                g += green
                b += blue
            total_pixels += 1
    
        n = len(pixels)
        r_avg = r / n
        g_avg = g / n
        b_avg = b / n
        rgb = [r_avg, g_avg, b_avg]
    
        # If computed average below darkness threshold, set to the threshold
        for index, item in enumerate(rgb):
            if item <= self.LOW_THRESHOLD:
                rgb[index] = self.LOW_THRESHOLD
    
        rgb = (rgb[0], rgb[1], rgb[2])
    
        data = {
            'rgb': rgb,
            #'dark_ratio': float(dark_pixels) / float(total_pixels) * 100,
            'bri': self.get_brightness(minBri, maxBri, float(dark_pixels) / float(total_pixels) * 100)
        }
        return data
    
    
        # Return modified Hue brightness value from ratio of dark pixels
    def get_brightness(self, minBri, maxBri, dark_pixel_ratio):
        #max_bri = int(maxBri)
        #min_bri = int(minBri)
    
        normal_range = max(1, maxBri - 1)
        new_range = maxBri - minBri
    
        brightness = maxBri - (dark_pixel_ratio * maxBri) / 100
        scaled_brightness = (((brightness - 1) * new_range) / normal_range) + float(minBri) + 1
    
        # Global brightness check
        if int(scaled_brightness) < int(minBri):
            scaled_brightness = int(minBri)
        elif int(scaled_brightness) > int(maxBri):
            scaled_brightness = int(maxBri)
    
        return int(scaled_brightness)
