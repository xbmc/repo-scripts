# -*- coding: utf-8 -*-
"""Viewing distance arithmetic. Pure functions, no Kodi imports (tested outside Kodi)."""
import math

INCH = 2.54
# Typical seated eye height in inches; the screen centre is placed near it.
SEATED_EYE_HEIGHT = 42.0


def screen_size(diagonal):
    """Width and height (inches) of a 16:9 screen with the given diagonal."""
    k = math.hypot(16.0, 9.0)
    return diagonal * 16.0 / k, diagonal * 9.0 / k


def distance_for_angle(diagonal, angle_deg):
    """Seating distance (inches) at which the screen fills the given horizontal viewing angle."""
    width, _ = screen_size(diagonal)
    return (width / 2.0) / math.tan(math.radians(angle_deg) / 2.0)


def diagonal_for_distance(distance, angle_deg):
    """16:9 diagonal (inches) that fills the given viewing angle at the seating distance."""
    width = 2.0 * distance * math.tan(math.radians(angle_deg) / 2.0)
    return width * math.hypot(16.0, 9.0) / 16.0


def mount_height(diagonal, eye_height=SEATED_EYE_HEIGHT):
    """Height (inches) of the screen's bottom edge so its centre is at eye height."""
    _, height = screen_size(diagonal)
    return eye_height - height / 2.0


def report_for_tv(diagonal):
    width, height = screen_size(diagonal)
    smpte = distance_for_angle(diagonal, 30.0)
    thx = distance_for_angle(diagonal, 40.0)
    bottom = mount_height(diagonal)
    return [
        '{0:g} in 16:9 TV: {1:.1f} x {2:.1f} in ({3:.0f} x {4:.0f} cm)'.format(
            diagonal, width, height, width * INCH, height * INCH),
        'Seating distance, 30 deg (SMPTE): {0:.0f} in ({1:.1f} ft, {2:.2f} m)'.format(
            smpte, smpte / 12.0, smpte * INCH / 100.0),
        'Seating distance, 40 deg (THX): {0:.0f} in ({1:.1f} ft, {2:.2f} m)'.format(
            thx, thx / 12.0, thx * INCH / 100.0),
        'Screen centre at {0:.0f} in seated eye height: bottom edge at about {1:.0f} in ({2:.0f} cm)'.format(
            SEATED_EYE_HEIGHT, bottom, bottom * INCH),
    ]


def report_for_distance(distance):
    low = diagonal_for_distance(distance, 30.0)
    high = diagonal_for_distance(distance, 40.0)
    return [
        'Seating distance {0:g} in ({1:.1f} ft, {2:.2f} m)'.format(distance, distance / 12.0, distance * INCH / 100.0),
        'TV size for 30 deg (SMPTE): about {0:.0f} in'.format(low),
        'TV size for 40 deg (THX): about {0:.0f} in'.format(high),
    ]
