"""Expression parsing for $MATH and $IF template features.

$MATH - Arithmetic expressions with property substitution:
    $MATH[id * 100 + 5000]
    $MATH[(mainmenuid * 1000) + 600 + id]

$IF - Conditional expressions:
    $IF[condition THEN trueValue ELSE falseValue]
    $IF[cond1 THEN val1 ELIF cond2 THEN val2 ELSE val3]
"""

from __future__ import annotations

import re

from .conditions import evaluate_condition
from .log import get_logger

log = get_logger("Expressions")


class MathEvaluator:
    """Simple arithmetic expression evaluator.

    Supports: +, -, *, /, //, %, parentheses, and property variables.
    All property values are automatically converted to numbers.
    """

    def __init__(self, variables: dict[str, str]):
        self.variables = variables
        self.pos = 0
        self.expr = ""

    def evaluate(self, expr: str) -> str:
        """Evaluate a math expression and return result as string."""
        self.expr = expr.strip()
        self.pos = 0

        try:
            result = self._parse_expression()
            self._skip_whitespace()
            if self.pos < len(self.expr):
                raise ValueError(f"Unexpected character: {self.expr[self.pos]}")
            # Return as int if whole number, else float
            if isinstance(result, float) and result.is_integer():
                return str(int(result))
            return str(result)
        except (ValueError, ZeroDivisionError) as e:
            log.debug(f"Math eval failed for '{expr}': {e}")
            return expr

    def _skip_whitespace(self) -> None:
        while self.pos < len(self.expr) and self.expr[self.pos].isspace():
            self.pos += 1

    def _parse_expression(self) -> float:
        """Parse addition and subtraction (lowest precedence)."""
        left = self._parse_term()

        while self.pos < len(self.expr):
            self._skip_whitespace()
            if self.pos >= len(self.expr):
                break

            op = self.expr[self.pos]
            if op == "+":
                self.pos += 1
                left = left + self._parse_term()
            elif op == "-":
                self.pos += 1
                left = left - self._parse_term()
            else:
                break

        return left

    def _parse_term(self) -> float:
        """Parse multiplication, division, modulo (higher precedence)."""
        left = self._parse_unary()

        while self.pos < len(self.expr):
            self._skip_whitespace()
            if self.pos >= len(self.expr):
                break

            # Check for // (floor division) first
            if self.expr[self.pos : self.pos + 2] == "//":
                self.pos += 2
                right = self._parse_unary()
                left = float(int(left) // int(right))
            elif self.expr[self.pos] == "*":
                self.pos += 1
                left = left * self._parse_unary()
            elif self.expr[self.pos] == "/":
                self.pos += 1
                right = self._parse_unary()
                if right == 0:
                    raise ZeroDivisionError("Division by zero")
                left = left / right
            elif self.expr[self.pos] == "%":
                self.pos += 1
                right = self._parse_unary()
                if right == 0:
                    raise ZeroDivisionError("Modulo by zero")
                left = left % right
            else:
                break

        return left

    def _parse_unary(self) -> float:
        """Parse unary minus."""
        self._skip_whitespace()

        if self.pos < len(self.expr) and self.expr[self.pos] == "-":
            self.pos += 1
            return -self._parse_unary()
        if self.pos < len(self.expr) and self.expr[self.pos] == "+":
            self.pos += 1
            return self._parse_unary()

        return self._parse_primary()

    def _parse_primary(self) -> float:
        """Parse numbers, variables, and parenthesized expressions."""
        self._skip_whitespace()

        if self.pos >= len(self.expr):
            raise ValueError("Unexpected end of expression")

        # Parenthesized expression
        if self.expr[self.pos] == "(":
            self.pos += 1
            result = self._parse_expression()
            self._skip_whitespace()
            if self.pos >= len(self.expr) or self.expr[self.pos] != ")":
                raise ValueError("Missing closing parenthesis")
            self.pos += 1
            return result

        # Number (integer or float)
        if self.expr[self.pos].isdigit() or self.expr[self.pos] == ".":
            return self._parse_number()

        # Variable name (property)
        if self.expr[self.pos].isalpha() or self.expr[self.pos] == "_":
            return self._parse_variable()

        raise ValueError(f"Unexpected character: {self.expr[self.pos]}")

    def _parse_number(self) -> float:
        """Parse a numeric literal."""
        start = self.pos
        has_dot = False

        while self.pos < len(self.expr):
            c = self.expr[self.pos]
            if c.isdigit():
                self.pos += 1
            elif c == "." and not has_dot:
                has_dot = True
                self.pos += 1
            else:
                break

        return float(self.expr[start : self.pos])

    def _parse_variable(self) -> float:
        """Parse a variable name and return its numeric value."""
        start = self.pos

        while self.pos < len(self.expr):
            c = self.expr[self.pos]
            if c.isalnum() or c == "_" or c == ".":
                self.pos += 1
            else:
                break

        name = self.expr[start : self.pos]
        value = self.variables.get(name, "0")

        try:
            return float(value) if value else 0.0
        except ValueError:
            return 0.0


def evaluate_math(expr: str, properties: dict[str, str]) -> str:
    """Evaluate a $MATH expression.

    Args:
        expr: The expression inside $MATH[...] (without the $MATH[] wrapper)
        properties: Property values available as variables

    Returns:
        The computed result as a string, or the original expression on error.
    """
    evaluator = MathEvaluator(properties)
    return evaluator.evaluate(expr)


def evaluate_if(expr: str, properties: dict[str, str]) -> str:
    """Evaluate a $IF expression.

    Syntax:
        condition THEN trueValue
        condition THEN trueValue ELSE falseValue
        cond1 THEN val1 ELIF cond2 THEN val2 ELSE val3

    Args:
        expr: The expression inside $IF[...] (without the $IF[] wrapper)
        properties: Property values for condition evaluation

    Returns:
        The selected value based on condition evaluation.
    """
    expr = expr.strip()

    # Parse ELIF chains: split into (condition, value) pairs + optional else
    clauses: list[tuple[str, str]] = []
    else_value: str | None = None

    remaining = expr
    while remaining:
        remaining = remaining.strip()

        # Find THEN keyword
        then_match = re.search(r"\bTHEN\b", remaining, re.IGNORECASE)
        if not then_match:
            # No more THEN, treat remainder as else value if we have clauses
            if clauses and remaining:
                else_value = remaining
            break

        condition = remaining[: then_match.start()].strip()
        after_then = remaining[then_match.end() :].strip()

        # Find the value: everything until ELIF, ELSE, or end
        elif_match = re.search(r"\bELIF\b", after_then, re.IGNORECASE)
        else_match = re.search(r"\bELSE\b", after_then, re.IGNORECASE)

        # Determine where value ends
        end_pos = len(after_then)
        next_keyword = None

        if elif_match and (not else_match or elif_match.start() < else_match.start()):
            end_pos = elif_match.start()
            next_keyword = "ELIF"
        elif else_match:
            end_pos = else_match.start()
            next_keyword = "ELSE"

        value = after_then[:end_pos].strip()
        clauses.append((condition, value))

        if next_keyword == "ELIF" and elif_match:
            remaining = after_then[elif_match.end() :]
        elif next_keyword == "ELSE" and else_match:
            else_value = after_then[else_match.end() :].strip()
            break
        else:
            break

    # Evaluate clauses in order
    for condition, value in clauses:
        if evaluate_condition(condition, properties):
            return value

    # Return else value or empty string
    return else_value if else_value is not None else ""


def process_math_expressions(
    text: str,
    properties: dict[str, str],
) -> str:
    """Process all $MATH[...] expressions in text.

    Args:
        text: Text potentially containing $MATH[...] expressions
        properties: Property values available as variables

    Returns:
        Text with all $MATH expressions evaluated.
    """
    pattern = re.compile(r"\$MATH\[([^\]]+)\]")

    def replace(match: re.Match) -> str:
        return evaluate_math(match.group(1), properties)

    return pattern.sub(replace, text)


def process_if_expressions(
    text: str,
    properties: dict[str, str],
) -> str:
    """Process all $IF[...] expressions in text.

    Args:
        text: Text potentially containing $IF[...] expressions
        properties: Property values available as variables

    Returns:
        Text with all $IF expressions evaluated.
    """
    pattern = re.compile(r"\$IF\[([^\]]+)\]")

    def replace(match: re.Match) -> str:
        return evaluate_if(match.group(1), properties)

    return pattern.sub(replace, text)
