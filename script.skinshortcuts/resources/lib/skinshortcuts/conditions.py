"""Condition evaluation utilities for Skin Shortcuts."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import TypeVar

try:
    import xbmc

    IN_KODI = True
except ImportError:
    IN_KODI = False

NO_SUFFIX_PROPERTIES = frozenset({
    "name",
    "label",
    "disabled",
    "default",
    "menu",
    "index",
    "id",
    "idprefix",
    "suffix",
})

V = TypeVar("V")

_OPERATOR_PATTERN = re.compile(r"[=~]")
_NOSUFFIX_PATTERN = re.compile(r"\{NOSUFFIX:[^}]+\}")
_HELD_PATTERN = re.compile(r"\x00(\d+)\x00")
_SLOT_PATTERN = re.compile(r"\.\d+$")
_CONDITION_MATCH_PATTERN = re.compile(r"^(!?)([a-zA-Z_][a-zA-Z0-9_\.]*)(=|~)(.*)$")

# Keyword to symbol mappings (applied with word boundaries)
_KEYWORD_REPLACEMENTS = [
    (re.compile(r"\bAND\b"), "+"),
    (re.compile(r"\bOR\b"), "|"),
    (re.compile(r"\bNOT\b"), "!"),
    (re.compile(r"\bEQUALS\b"), "="),
    (re.compile(r"\bCONTAINS\b"), "~"),
]


def lookup(name: str, *sources: Mapping[str, V]) -> V | None:
    """The value under a property name, exact across the sources, then ignoring case."""
    for source in sources:
        if name in source:
            return source[name]
    folded = name.lower()
    for source in sources:
        for key, value in source.items():
            if key.lower() == folded:
                return value
    return None


def _normalize_keywords(condition: str) -> str:
    """Normalize keyword operators (AND, OR, NOT, EQUALS, CONTAINS) to their symbols."""
    for pattern, replacement in _KEYWORD_REPLACEMENTS:
        condition = pattern.sub(replacement, condition)
    return condition


def expand_compact_or(condition: str) -> str:
    """Expand compact OR syntax, so "a=x | y" becomes "a=x | a=y"."""
    if not condition:
        return condition

    result_parts = []
    and_parts = _split_preserving_brackets(condition, "+")

    for and_part in and_parts:
        and_part = and_part.strip()
        if not and_part:
            continue

        is_negated = and_part.startswith("!")
        if is_negated:
            and_part = and_part[1:].strip()

        if and_part.startswith("[") and and_part.endswith("]"):
            inner = and_part[1:-1].strip()
            expanded_inner = _expand_or_segment(inner)
            if is_negated:
                result_parts.append(f"![{expanded_inner}]")
            else:
                result_parts.append(f"[{expanded_inner}]")
        else:
            expanded = _expand_or_segment(and_part)
            if is_negated:
                result_parts.append(f"!{expanded}")
            else:
                result_parts.append(expanded)

    return " + ".join(result_parts)


def _split_preserving_brackets(text: str, delimiter: str) -> list[str]:
    """Split text by delimiter but preserve content inside brackets."""
    parts = []
    current = []
    depth = 0

    for char in text:
        if char == "[":
            depth += 1
            current.append(char)
        elif char == "]":
            depth -= 1
            current.append(char)
        elif char == delimiter and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)

    if current:
        parts.append("".join(current))

    return parts


def _expand_or_segment(segment: str) -> str:
    """Expand a single OR segment."""
    parts = _split_preserving_brackets(segment, "|")
    if len(parts) <= 1:
        return segment

    result_parts = []
    current_property = ""
    current_operator = ""

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # a group is a condition of its own, never a bare value for the running property
        stripped = part.lstrip("!")
        if stripped.startswith("["):
            if _is_wrapped_in_brackets(stripped):
                negation = part[: len(part) - len(stripped)]
                part = f"{negation}[{expand_compact_or(stripped[1:-1])}]"
            result_parts.append(part)
            continue

        match = _CONDITION_MATCH_PATTERN.match(part)
        if match:
            negation = match.group(1)
            current_property = match.group(2)
            current_operator = match.group(3)
            value = match.group(4)
            result_parts.append(f"{negation}{current_property}{current_operator}{value}")
        elif current_property:
            result_parts.append(f"{current_property}{current_operator}{part}")
        else:
            result_parts.append(part)

    return " | ".join(result_parts)


def evaluate_condition(condition: str, properties: dict[str, str]) -> bool:
    """Evaluate a condition against property values."""
    if not condition:
        return True

    condition = condition.strip()
    if not condition:
        return True

    condition = _normalize_keywords(condition)

    if "|" in condition:
        condition = expand_compact_or(condition)
    return _evaluate_expanded(condition, properties)


def _is_wrapped_in_brackets(text: str) -> bool:
    """Whether text is wrapped in matching brackets (not just starts/ends with them)."""
    if not text.startswith("[") or not text.endswith("]"):
        return False
    depth = 0
    for i, char in enumerate(text):
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0 and i < len(text) - 1:
                return False
    return depth == 0


def _evaluate_expanded(condition: str, properties: dict[str, str]) -> bool:
    """Evaluate an expanded condition."""
    condition = condition.strip()
    if not condition:
        return True

    if _is_wrapped_in_brackets(condition):
        return _evaluate_expanded(condition[1:-1], properties)

    # Split AND/OR before negation: !a + b = (!a) + b, not !(a + b)
    # OR splits first so AND binds tighter, as Kodi's own conditions do
    or_parts = _split_preserving_brackets(condition, "|")
    if len(or_parts) > 1:
        return any(_evaluate_expanded(part.strip(), properties) for part in or_parts)

    and_parts = _split_preserving_brackets(condition, "+")
    if len(and_parts) > 1:
        return all(_evaluate_expanded(part.strip(), properties) for part in and_parts)

    if condition.startswith("!"):
        inner = condition[1:].strip()
        if _is_wrapped_in_brackets(inner):
            return not _evaluate_expanded(inner[1:-1], properties)
        return not _evaluate_single(inner, properties)

    return _evaluate_single(condition, properties)


def _matches(actual: str, value: str) -> bool:
    """Value comparison, case insensitive when the value is a boolean."""
    if value.lower() in ("true", "false"):
        return actual.lower() == value.lower()
    return actual == value


def _evaluate_single(condition: str, properties: dict[str, str]) -> bool:
    """Evaluate a single condition (property=value or property~value)."""
    condition = condition.strip()

    negated = False
    if condition.startswith("!"):
        negated = True
        condition = condition[1:].strip()

    if _is_wrapped_in_brackets(condition):
        result = _evaluate_expanded(condition[1:-1], properties)
        return not result if negated else result

    if condition.endswith(" EMPTY"):
        prop_name = condition[:-6].strip()
        actual = lookup(prop_name, properties) or ""
        result = actual == ""
        return not result if negated else result

    if " IN " in condition:
        prop_name, values_str = condition.split(" IN ", 1)
        prop_name = prop_name.strip()
        values_str = values_str.strip()
        actual = lookup(prop_name, properties) or ""
        values = [v.strip() for v in values_str.split(",")]
        result = any(_matches(actual, v) for v in values)
        return not result if negated else result

    operator = _OPERATOR_PATTERN.search(condition)
    if operator:
        prop_name = condition[: operator.start()].strip()
        value = condition[operator.end() :].strip()
        actual = lookup(prop_name, properties)
        if operator.group() == "~":
            result = value in (actual or "")
        elif actual is not None:
            result = _matches(actual, value)
        elif prop_name.lower() in ("true", "false"):
            # Literal boolean comparison (e.g., from $IF after $PROPERTY substitution)
            result = _matches(prop_name, value)
        else:
            result = _matches("", value)
        return not result if negated else result

    # Literal boolean value (e.g., from $PROPERTY substitution)
    if condition.lower() in ("true", "false"):
        result = condition.lower() == "true"
        return not result if negated else result

    # Property name only: truthy if non-empty (but "false" string is falsy)
    val = lookup(condition, properties) or ""
    if val.lower() in ("true", "false"):
        result = val.lower() == "true"
    else:
        result = bool(val)
    return not result if negated else result


def check_visible(condition: str) -> bool:
    """Check a Kodi visibility condition; empty passes, as does anything outside Kodi."""
    if not condition or not IN_KODI:
        return True
    return xbmc.getCondVisibility(condition)


def suffix_condition(condition: str, suffix: str) -> str:
    """Suffix each property name the evaluator reads, leaving values and slots alone."""
    if not suffix or not condition:
        return condition

    held: list[str] = []

    def hold(match: re.Match) -> str:
        held.append(match.group(0))
        return f"[\x00{len(held) - 1}\x00]"

    text = _normalize_keywords(_NOSUFFIX_PATTERN.sub(hold, condition)).strip()
    if "|" in text:
        text = expand_compact_or(text)
    text = _suffix_expression(text, suffix)
    return _HELD_PATTERN.sub(lambda m: held[int(m.group(1))], text)


def _suffix_expression(condition: str, suffix: str) -> str:
    """Rebuild a condition along the evaluator's own split, suffixing each term."""
    condition = condition.strip()
    if _is_wrapped_in_brackets(condition):
        return f"[{_suffix_expression(condition[1:-1], suffix)}]"

    for delimiter in ("|", "+"):
        parts = _split_preserving_brackets(condition, delimiter)
        if len(parts) > 1:
            return f" {delimiter} ".join(_suffix_expression(p, suffix) for p in parts)

    if condition.startswith("!"):
        return f"!{_suffix_expression(condition[1:], suffix)}"
    return _suffix_term(condition, suffix)


def _suffix_term(term: str, suffix: str) -> str:
    """Suffix the property name of one comparison, EMPTY, IN or presence check."""

    def slot(name: str) -> str:
        name = name.strip()
        if (
            not name
            or name in NO_SUFFIX_PROPERTIES
            or name.startswith("$")
            or "\x00" in name
            or _SLOT_PATTERN.search(name)
        ):
            return name
        return f"{name}{suffix}"

    if term.endswith(" EMPTY"):
        return f"{slot(term[:-6])} EMPTY"
    if " IN " in term:
        name, values = term.split(" IN ", 1)
        return f"{slot(name)} IN {values.strip()}"
    operator = _OPERATOR_PATTERN.search(term)
    if operator:
        value = term[operator.end() :].strip()
        return f"{slot(term[: operator.start()])}{operator.group()}{value}"
    if term.lower() in ("true", "false"):
        return term
    return slot(term)
