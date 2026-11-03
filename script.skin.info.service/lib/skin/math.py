"""Math expression evaluation utilities for skin integration."""
import ast
import operator
import xbmc
from lib.kodi.client import log
from lib.kodi.utilities import set_window_prop, clear_window_prop
from lib.skin.labels import resolve_label


_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def safe_eval_math(expression):
    """Evaluate math expression via AST; supports `+ - * / // % **` and parens. None on failure."""
    try:
        node = ast.parse(expression, mode='eval').body

        def _eval(node):
            """Evaluate one AST node, refusing anything outside the allowed operators."""
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.BinOp):
                left = _eval(node.left)
                right = _eval(node.right)
                op = _ALLOWED_OPERATORS.get(type(node.op))
                if op is None:
                    raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
                return op(left, right)
            elif isinstance(node, ast.UnaryOp):
                operand = _eval(node.operand)
                op = _ALLOWED_OPERATORS.get(type(node.op))
                if op is None:
                    raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
                return op(operand)
            else:
                raise ValueError(f"Unsupported expression type: {type(node).__name__}")

        return _eval(node)

    except (SyntaxError, ValueError, ZeroDivisionError, TypeError) as e:
        log("SkinUtils", f"Math evaluation failed: {e}", xbmc.LOGWARNING)
        return None


def evaluate_math(expression, prefix='', window='home'):
    """Evaluate a math expression, skin labels resolved, into `SkinInfo.Math.*.Result`."""
    prop_name = f'SkinInfo.Math.{prefix}.Result' if prefix else 'SkinInfo.Math.Result'

    if not expression:
        clear_window_prop(prop_name, window)
        return

    resolved_expression = resolve_label(expression) if '$' in expression else expression
    result = safe_eval_math(resolved_expression)

    if result is not None:
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        set_window_prop(prop_name, result, window)
    else:
        clear_window_prop(prop_name, window)
