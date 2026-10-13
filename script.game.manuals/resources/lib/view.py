# -*- coding: utf-8 -*-
"""Where a page sits on screen at a given zoom.

The page is an image control the window moves and resizes. At the whole-page
zoom it fits the area and is centred; zoomed in, it is larger than the area
and the view is kept on the page, so no edge ever shows background.
"""

#: Zoom factors over the whole-page size, in the order the zoom steps through
ZOOMS = (1.0, 1.5, 2.0, 3.0, 4.0)
#: How far one pan moves, as a share of the area
PAN_STEP = 0.2


class View(object):
    def __init__(self, area_width, area_height):
        self.area = (area_width, area_height)
        self.page = (area_width, area_height)
        self.zoom = 0
        # The point of the page at the centre of the area, as shares of the page
        self.centre = [0.5, 0.5]

    def show(self, width, height):
        """A new page: whole, centred."""
        self.page = (max(width, 1), max(height, 1))
        self.whole()

    def whole(self):
        changed = self.zoom != 0
        self.zoom = 0
        self.centre = [0.5, 0.5]
        return changed

    @property
    def is_whole(self):
        return self.zoom == 0

    def step(self, steps):
        """Zoom by a number of steps, keeping the same point in the middle."""
        zoom = min(max(self.zoom + steps, 0), len(ZOOMS) - 1)
        changed = zoom != self.zoom
        self.zoom = zoom
        self._clamp()
        return changed

    def pan(self, dx, dy):
        """Move the view by steps across and down; False if already at that edge."""
        width, height = self.size()
        before = list(self.centre)
        self.centre[0] += dx * PAN_STEP * self.area[0] / width
        self.centre[1] += dy * PAN_STEP * self.area[1] / height
        self._clamp()
        return self.centre != before

    def size(self):
        """The page's size on screen at the current zoom."""
        fit = min(self.area[0] / float(self.page[0]), self.area[1] / float(self.page[1]))
        scale = fit * ZOOMS[self.zoom]
        return self.page[0] * scale, self.page[1] * scale

    def rect(self):
        """The page's x, y, width and height, relative to the area."""
        width, height = self.size()
        x = self.area[0] / 2.0 - self.centre[0] * width
        y = self.area[1] / 2.0 - self.centre[1] * height
        return int(round(x)), int(round(y)), int(round(width)), int(round(height))

    def _clamp(self):
        width, height = self.size()
        for axis, extent in ((0, width), (1, height)):
            half = self.area[axis] / 2.0 / extent
            if half >= 0.5:
                # Smaller than the area along this axis: centred
                self.centre[axis] = 0.5
            else:
                self.centre[axis] = min(max(self.centre[axis], half), 1.0 - half)
