import unittest
from typing import Mapping, Type

from lib.unit.temperature import (
    Temperature, TemperatureCelsius, TemperatureFahrenheit, TemperatureKelvin, TemperatureReaumur, TemperatureRankine,
    TemperatureRomer, TemperatureDelisle, TemperatureNewton, TemperatureUnits
)

SAMPLE = 345.67

CONVERT_42SI_TO: Mapping[Type[Temperature], float] = {
    TemperatureCelsius: 72.52,
    TemperatureFahrenheit: 162.5,
    TemperatureKelvin: 345.67,
    TemperatureReaumur: 58.02,
    TemperatureRankine: 622.2,
    TemperatureRomer: 45.57,
    TemperatureDelisle: 41.2,
    TemperatureNewton: 23.93,
}


class TestTemperatureUnits(unittest.TestCase):
    def test_unit_identity_via_from_si(self):
        for unit in TemperatureUnits.values():
            with self.subTest(msg=unit.unit):
                self.assertAlmostEqual(SAMPLE, unit.from_si_value(unit(SAMPLE).si_value()).value)

    def test_si_identity_via_unit(self):
        for unit in TemperatureUnits.values():
            with self.subTest(msg=unit.unit):
                self.assertAlmostEqual(SAMPLE, unit.from_si_value(SAMPLE).si_value())

    def test_unit_from_si(self):
        for unit in TemperatureUnits.values():
            with self.subTest(msg=unit.unit):
                self.assertLess(
                    abs(CONVERT_42SI_TO[unit] - unit.from_si_value(SAMPLE).value) / CONVERT_42SI_TO[unit], 1e-3
                )

    def test_si_from_unit(self):
        for unit in TemperatureUnits.values():
            with self.subTest(msg=unit.unit):
                self.assertLess(abs(SAMPLE - unit(CONVERT_42SI_TO[unit]).si_value()) / SAMPLE, 1e-3)


if __name__ == '__main__':
    unittest.main()
