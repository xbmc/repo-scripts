import unittest
from typing import Mapping, Type

from lib.unit.speed import (
    SpeedUnits, SpeedBft, SpeedKph, SpeedMpmin, SpeedMps, SpeedFtph, SpeedFtpm, SpeedFtps, SpeedMph, SpeedKts,
    SpeedInps, SpeedYdps, SpeedFpf, Speed
)

SAMPLE = 42.0

CONVERT_42SI_TO: Mapping[Type[Speed], float] = {
    SpeedKph: 151.2,
    SpeedMpmin: 2520.0,
    SpeedMps: 42.0,
    SpeedFtph: 496063.0,
    SpeedFtpm: 8268.0,
    SpeedFtps: 137.8,
    SpeedMph: 93.95,
    SpeedKts: 81.64,
    SpeedBft: 12,
    SpeedInps: 1653.54,
    SpeedYdps: 45.93,
    SpeedFpf: 252541.0,
}


class TestSpeedUnits(unittest.TestCase):
    def test_unit_identity_via_from_si(self):
        for unit in SpeedUnits.values():
            if unit == SpeedBft:
                with self.subTest(msg=unit.unit):
                    self.assertEqual(10, unit.from_si_value(unit(10.0).si_value()).value)
            else:
                with self.subTest(msg=unit.unit):
                    self.assertAlmostEqual(SAMPLE, unit.from_si_value(unit(SAMPLE).si_value()).value)

    def test_si_identity_via_unit(self):
        for unit in SpeedUnits.values():
            if unit == SpeedBft:
                with self.subTest(msg=unit.unit):
                    # i hope bft scale won't change ;)
                    self.assertAlmostEqual(0.3, float(unit.from_si_value(0.3).si_value()))
            else:
                with self.subTest(msg=unit.unit):
                    self.assertAlmostEqual(SAMPLE, unit.from_si_value(SAMPLE).si_value())

    def test_unit_from_si(self):
        for unit in SpeedUnits.values():
            if unit == SpeedBft:
                with self.subTest(msg=unit.unit):
                    self.assertEqual(CONVERT_42SI_TO[unit], unit.from_si_value(SAMPLE).value)
            else:
                with self.subTest(msg=unit.unit):
                    self.assertLess(
                        abs(CONVERT_42SI_TO[unit] - unit.from_si_value(SAMPLE).value) / CONVERT_42SI_TO[unit], 1e-4
                    )

    def test_si_from_unit(self):
        for unit in SpeedUnits.values():
            if unit == SpeedBft:
                # this test would make even less sense than the last ones
                continue
            else:
                with self.subTest(msg=unit.unit):
                    self.assertLess(abs(SAMPLE - unit(CONVERT_42SI_TO[unit]).si_value()) / SAMPLE, 1e-4)


if __name__ == '__main__':
    unittest.main()
