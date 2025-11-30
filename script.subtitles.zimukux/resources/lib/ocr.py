# -*- coding: utf-8 -*-
"""
Subtitle add-on for Kodi 19+ derived from https://github.com/taxigps/xbmc-addons-chinese/tree/master/service.subtitles.zimuku
Copyright (C) <2021>  <root@wokanxing.info>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

"""
A simple OCR script to recognize 5 digits from a Base64 encoded BMP image,
using only standard Python libraries.

This script is designed to work in restricted environments like Kodi add-ons.
"""
import base64
import struct
import sys
from typing import Tuple, List


class BmpOcr:
    """
    Performs OCR on a specific 100x27 24-bit BMP image of 5 digits.

    The method uses template matching based on a few sample pixels
    for each character.
    """
    # Image properties
    IMG_WIDTH = 100
    IMG_HEIGHT = 27
    CHAR_WIDTH = 20
    NUM_CHARS = 5

    # BMP header constants
    PIXEL_DATA_OFFSET = 54  # For 24-bit BMP without a color palette

    # OCR sampling points relative to the top-left of a 20x27 character box.
    # These points are chosen to effectively distinguish between digits 0-9.
    # (x, y)
    SAMPLE_POINTS = [
        (10, 7),   # P0: Top-center
        (7, 8),    # P1: Top-left
        (12, 8),   # P2: Top-right
        (10, 13),  # P3: Center
        (7, 19),   # P4: Bottom-left
        (12, 19),  # P5: Bottom-right
        (10, 20),  # P6: Bottom-center
        (6, 13),   # P7: Middle-left
        (14, 13)   # P8: Middle-right
    ]

    # Pre-defined feature vectors for digits 0-9.
    # 1 represents a foreground (dark) pixel, 0 represents a background (light) pixel.
    # The vectors for '1', '2', '6', '7', '8' are derived from the sample image.
    # The rest are crafted based on a standard digital font shape.
    DIGIT_TEMPLATES = {
        '0': [1, 1, 1, 1, 1, 1, 1, 1, 0],#
        '1': [0, 1, 0, 0, 0, 0, 1, 0, 0],#
        '2': [1, 0, 1, 0, 1, 0, 1, 0, 0],#
        '3': [1, 0, 1, 1, 0, 1, 1, 0, 0],#
        '4': [0, 0, 1, 0, 0, 1, 0, 0, 0],#
        '5': [1, 1, 0, 0, 0, 1, 1, 0, 0],#
        '6': [1, 0, 1, 1, 1, 1, 1, 1, 0],#
        '7': [1, 0, 1, 0, 0, 0, 0, 0, 0],#
        '8': [1, 1, 1, 1, 1, 1, 1, 0, 0],#
        '9': [1, 1, 1, 0, 1, 0, 1, 0, 0],#
    }

    def __init__(self, b64_string: str):
        """
        Initializes the OCR with a Base64 encoded BMP string.
        """
        try:
            self.image_data = base64.b64decode(b64_string)
        except (ValueError, TypeError):
            raise ValueError("Invalid Base64 string provided.")

        # Basic validation of the BMP header
        if len(self.image_data) < self.PIXEL_DATA_OFFSET or self.image_data[0:2] != b'BM':
            raise ValueError("Data is not a valid BMP.")

        width = struct.unpack_from('<i', self.image_data, 18)[0]
        height = struct.unpack_from('<i', self.image_data, 22)[0]

        if width != self.IMG_WIDTH or height != self.IMG_HEIGHT:
            raise ValueError(f"Expected image dimensions {self.IMG_WIDTH}x{self.IMG_HEIGHT}, "
                             f"but got {width}x{height}.")

        # Calculate row size with padding (stride)
        self.row_stride = (self.IMG_WIDTH * 3 + 3) & ~3

    def _get_pixel(self, x: int, y: int) -> Tuple[int, int, int]:
        """
        Gets the (B, G, R) color tuple for a pixel at (x, y).
        Handles the bottom-up row order of BMP files.
        """
        # BMP rows are stored bottom-up
        bmp_y = self.IMG_HEIGHT - 1 - y
        offset = self.PIXEL_DATA_OFFSET + (bmp_y * self.row_stride) + (x * 3)
        b, g, r = self.image_data[offset:offset + 3]
        return b, g, r

    def _is_foreground(self, x: int, y: int, threshold: int = 70) -> bool:
        """
        Determines if a pixel is part of the foreground (a digit).
        The digits are dark gray/black, background is light gray.
        """
        b, g, r = self._get_pixel(x, y)
        # Use average brightness to determine if it's foreground
        return (r + g + b) / 3 < threshold

    def _match_digit(self, feature_vector: List[int]) -> str:
        """
        Finds the best matching digit for a given feature vector.
        It calculates the Hamming distance between the input vector and each template.
        """
        min_diff = float('inf')
        found_digit = '?'

        for digit_char, template_vector in self.DIGIT_TEMPLATES.items():
            # Calculate Hamming distance (number of differing bits)
            diff = sum(v1 != v2 for v1, v2 in zip(feature_vector, template_vector))

            if diff < min_diff:
                min_diff = diff
                found_digit = digit_char

            # Perfect match, no need to check further
            if min_diff == 0:
                break

        return found_digit

    def recognize(self) -> str:
        """
        Recognizes all 5 digits in the image and returns them as a string.
        """
        result = []
        one_offset = 0
        for i in range(self.NUM_CHARS):
            char_x_offset = i * self.CHAR_WIDTH

            # Generate the feature vector for the current character
            feature_vector = [
                1 if self._is_foreground(char_x_offset + px - one_offset, py) else 0
                for px, py in self.SAMPLE_POINTS
            ]
            print(feature_vector)

            # Find the best match for the vector
            recognized_char = self._match_digit(feature_vector)
            if recognized_char == '1':
                one_offset += 1
            elif recognized_char == '4':
                one_offset -= 1

            result.append(recognized_char)

        return "".join(result)


def main():
    """
    Main function to run the OCR process.
    """

    # parse file path from first argument
    if len(sys.argv) < 2:
        b64_file_path = 'base64.txt'
    else:
        b64_file_path = sys.argv[1]

    try:
        with open(b64_file_path, 'r') as f:
            b64_data = f.read().strip()
    except FileNotFoundError:
        print(f"Error: The file '{b64_file_path}' was not found.", file=sys.stderr)
        sys.exit(1)

    if not b64_data:
        print(f"Error: The file '{b64_file_path}' is empty.", file=sys.stderr)
        sys.exit(1)

    try:
        ocr = BmpOcr(b64_data)
        result = ocr.recognize()
        print(f"Input {b64_file_path}")
        print(f"Recognized digits: {result}")
    except ValueError as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()