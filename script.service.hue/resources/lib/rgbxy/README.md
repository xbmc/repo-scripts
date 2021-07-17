# Philips Hue Python RGB / CIE1931 "xy" Converter

RGB conversion tool written in Python for Philips Hue.

```python
In [1]: from rgb_xy import Converter

In [2]: converter = Converter()
		
In [3]: converter.hex_to_xy('bada55')
Out[3]: [0.3991853917195425, 0.498424689144739]

In [4]: converter.rgb_to_xy(255, 0, 0)
Out[4]: [0.6484272236872118, 0.330856101472778]

In [5]: converter.get_random_xy_color()
Out[5]: [0.3706941388849757, 0.19786410488389355]

In [6]: converter.xy_to_hex(0.3991853917195425, 0.498424689144739, bri=0.8)
Out[6]: 'e9e860'
```

## Gamuts

The conversion tool support three gamuts: Gamut A, B, and C, [documented here](http://www.developers.meethue.com/documentation/supported-lights).  Use them as follows:

```python
from rgb_xy import Converter
from rgb_xy import GamutA # or GamutB, GamutC

converter = Converter(GamutA)
```

If no gamut is specified, defaults to Gamut B (A19 Gen 1 Hue bulbs).
