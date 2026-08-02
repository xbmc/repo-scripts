"""Math expression evaluation utilities for skin integration."""
import ast
import operator
import re
import xbmc
from lib.kodi.client import log


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
    """Evaluate a math expression and write the result to a window property.

    `$INFO[]`/`$VAR[]` references in `expression` are resolved before evaluation.
    Result goes to `SkinInfo.Math[.{prefix}].Result`.
    """
    prop_name = f'SkinInfo.Math.{prefix}.Result' if prefix else 'SkinInfo.Math.Result'

    if not expression:
        xbmc.executebuiltin(f'ClearProperty({prop_name},{window})')
        return

    resolved_expression = expression
    if '$INFO[' in expression or '$VAR[' in expression:
        infolabel_pattern = r'\$(?:INFO|VAR)\[[^\]]+\]'
        infolabels = re.findall(infolabel_pattern, expression)

        for infolabel in infolabels:
            resolved_value = xbmc.getInfoLabel(infolabel)
            resolved_expression = resolved_expression.replace(infolabel, resolved_value, 1)

    result = safe_eval_math(resolved_expression)

    if result is not None:
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        xbmc.executebuiltin(f'SetProperty({prop_name},{result},{window})')
    else:
        xbmc.executebuiltin(f'ClearProperty({prop_name},{window})')
