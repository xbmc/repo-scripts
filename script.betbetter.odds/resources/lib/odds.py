# -*- coding: utf-8 -*-
"""Pure odds maths, no Kodi imports (testable outside Kodi)."""
from fractions import Fraction


def parse(text):
    """Return decimal odds from an American, decimal or fractional price."""
    t = text.strip().replace(' ', '')
    if not t:
        raise ValueError('empty')
    if '/' in t:
        num, den = t.split('/', 1)
        value = Fraction(num) / Fraction(den)
        if value <= 0:
            raise ValueError('fraction must be positive')
        return 1 + float(value)
    number = float(t)
    if t.startswith(('+', '-')) or abs(number) >= 100:
        if abs(number) < 100:
            raise ValueError('American price must be <= -100 or >= +100')
        return 1 + number / 100 if number > 0 else 1 + 100 / abs(number)
    if number <= 1:
        raise ValueError('decimal odds must be above 1')
    return number


def to_american(decimal):
    if decimal >= 2:
        return '+{0}'.format(int(round((decimal - 1) * 100)))
    return str(int(round(-100 / (decimal - 1))))


def to_fractional(decimal):
    frac = Fraction(decimal - 1).limit_denominator(100)
    return '{0}/{1}'.format(frac.numerator, frac.denominator)


def describe(decimal):
    return ('Decimal: {0:.2f}\nAmerican: {1}\nFractional: {2}\n'
            'Implied probability: {3:.1f}%\nA 10-unit stake returns {4:.2f}').format(
        decimal, to_american(decimal), to_fractional(decimal), 100 / decimal, 10 * decimal)


def margin(prices):
    return sum(1 / p for p in prices) - 1


def fair(prices):
    total = sum(1 / p for p in prices)
    return [(1 / p) / total for p in prices]


def describe_market(prices):
    lines = []
    for i, (p, f) in enumerate(zip(prices, fair(prices)), 1):
        lines.append('Outcome {0}: decimal {1:.2f} ({2}), implied {3:.1f}%, fair {4:.1f}%'.format(
            i, p, to_american(p), 100 / p, 100 * f))
    lines.append('')
    lines.append('Bookmaker margin: {0:.2f}%'.format(100 * margin(prices)))
    return '\n'.join(lines)
