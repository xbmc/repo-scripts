# coding=utf-8

import ibis
import copy
import operator
import six

from .util import register_builtin
from lib.aspectratio import v_ar_ratio
from lib.logging import log as LOG
from ibis.context import Undefined


@ibis.filters.register('get')
def get_attr(obj, attr, fallback=None, default=None):
    if isinstance(attr, Undefined):
        return obj.get(fallback, default)
    return obj.get(attr, default)


@ibis.filters.register('calc')
@register_builtin
def calc(a, b, op="add"):
    if isinstance(a, six.string_types):
        a = float(a) if "." in a else int(a)
    elif isinstance(b, six.string_types):
        b = float(b) if "." in b else int(b)
    try:
        return getattr(operator, op)(a, b)
    except:
        raise ValueError("Can't calculate {}({}:{}, {}:{})".format(op, type(a), repr(a), type(b), repr(b)))


@ibis.filters.register('vscale', with_context=True)
@register_builtin
def vscale(value, up=1, negpos=False, context=None):
    """
    scale integer based on the aspect ratio difference between the current resolution and our default resolution

    up is there to optionally apply a factor on top of the scaled value. this is important for buttons without a set
    width, as they tend to get crushed

    negpos is used when we use negative absolute window position animations to position controls greater than our
    screen size, e.g. "scrolling" them. In this case we subtract the resulting scaled value from the original one,
    shifting it further into negativeness
    fixme: Not sure if this is universal
    """
    if not context.core.needs_scaling:
        return value

    cached_scale = context.get('cached_scale', None)
    if cached_scale is None:
        w, h = context.core.resolution
        cached_scale = v_ar_ratio(w, h)
        context.set_global("cached_scale", cached_scale)

    if negpos and value < 0:
        return value + round(cached_scale * value, 2) * up
    return round(cached_scale * value, 2) * up


@ibis.filters.register('vperc')
@register_builtin
def vperc(height, perc=50, ref=1080, rel=50, r=2):
    """
    return vertical position based on percentage of ref, percentage of height
    @param r:
    @param rel:
    @param perc:
    @param height:
    @param ref:
    @return: float
    """
    return round(perc * ref / 100.0 - height * rel / 100.0, r)


@ibis.filters.register('valign')
@register_builtin
def valign(height, align="middle"):
    if align == "middle":
        return vperc(height)
    elif align == "bottom":
        return vperc(height, perc=100, rel=100)


@ibis.filters.register('add')
@register_builtin
def add(a, b):
    return calc(a, b)


@ibis.filters.register('sub')
@register_builtin
def sub(a, b):
    return calc(a, b, op="sub")


@ibis.filters.register('div')
@register_builtin
def div(a, b):
    return calc(a, b, op="truediv")


@ibis.filters.register('mul')
@register_builtin
def mul(a, b):
    return calc(a, b, op="mul")


@ibis.filters.register('int')
@register_builtin
def cast_int(a):
    return int(a)


@ibis.filters.register('resolve', with_context=True)
@register_builtin('resolve')
def resolve_variable(arg, context=None):
    return ibis.nodes.ResolveContextVariable(arg)


@ibis.filters.register('merge_dict')
@ibis.filters.register('merge')
@register_builtin('merge')
def merge_dict(*args):
    final_dict = {}
    for arg in args:
        final_dict.update(copy.deepcopy(arg))

    return final_dict
