# SPDX-License-Identifier: GPL-2.0-only
"""Swapping a pairing code for the webhook token (docs/contract.md, Pairing).

Runs in the settings script, never in the service. Logs carry the outcome and the HTTP status
only: the code, the token, the address and the instance name stay off Kodi's shared log.
"""

from __future__ import annotations

import json
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from resources.lib.constants import PAIR_TIMEOUT_SECONDS
from resources.lib.log import get_logger
from resources.lib.reporter import InvalidWebhookUrl, open_connection, target_of

_log = get_logger("config")

WEBHOOK_PATH = "/webhook/kodiwatcher"
PAIR_PATH = f"{WEBHOOK_PATH}/pair"

Outcome = Literal["paired", "invalid_code", "rate_limited", "unreachable", "certificate", "failed"]


@dataclass(frozen=True)
class PairResult:
    outcome: Outcome
    token: str = ""
    instance: str = ""
    # The HTTP status, 0 when no response arrived. Shown for "failed" so a user can report it.
    status: int = 0


def normalise_address(text: str) -> str | None:
    """What a household types, as the CrossWatch base URL. None when it cannot be one.

    host:port is enough; http is assumed without a scheme. A pasted webhook URL is cut back
    to its base, so the address prefilled from the stored URL also works when typed again.
    """
    address = text.strip()
    if not address:
        return None
    # The scheme check comes before trimming slashes, or "http://" would read as a host.
    if "://" not in address:
        address = f"http://{address}"
    address = address.rstrip("/")
    if address.endswith(WEBHOOK_PATH):
        address = address[: -len(WEBHOOK_PATH)].rstrip("/")
    try:
        target = target_of(address)
    except InvalidWebhookUrl:
        return None
    if "?" in target.path or not target.host:
        return None
    return address


def address_hint(webhook_url: str) -> str:
    """The base address behind a stored webhook URL, to prefill the next pairing."""
    url = webhook_url.strip().rstrip("/")
    return url[: -len(WEBHOOK_PATH)] if url.endswith(WEBHOOK_PATH) else url


def normalise_code(text: str) -> str:
    """Uppercase, no spaces. CrossWatch ignores both too; this keeps the request plain."""
    return "".join(text.split()).upper()


def exchange_code(
    address: str,
    code: str,
    *,
    connect: Callable[..., Any] = open_connection,
    timeout: float = PAIR_TIMEOUT_SECONDS,
) -> PairResult:
    """One attempt, no retry: a code is single use, and the user is waiting at the screen."""
    target = target_of(f"{address}{PAIR_PATH}")
    body = json.dumps({"code": code}).encode("utf-8")
    try:
        connection = connect(target.scheme, target.host, target.port, timeout)
    except Exception as exc:
        return _transport_failure(exc)
    try:
        connection.request("POST", target.path, body=body, headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        status = int(getattr(response, "status", 0) or 0)
        raw = response.read()
    except Exception as exc:
        return _transport_failure(exc)
    finally:
        try:
            connection.close()
        except Exception:
            pass
    result = _verdict(status, raw)
    _log.info("config.pair_result", outcome=result.outcome, status=status)
    return result


def _transport_failure(exc: Exception) -> PairResult:
    # The server answered, but with a certificate Python does not trust (self-signed, or a
    # platform without a certificate store). Telling it apart from "unreachable" sends the
    # household to the certificate rather than to the network.
    outcome: Outcome = "certificate" if isinstance(exc, ssl.SSLCertVerificationError) else "unreachable"
    _log.warning("config.pair_failed", outcome=outcome, error=type(exc).__name__)
    return PairResult(outcome)


def _verdict(status: int, raw: bytes) -> PairResult:
    if status == 401:
        return PairResult("invalid_code", status=status)
    if status == 429:
        return PairResult("rate_limited", status=status)
    if status != 200:
        return PairResult("failed", status=status)
    try:
        parsed = json.loads(raw.decode("utf-8") or "{}")
    except ValueError:
        parsed = None
    if not isinstance(parsed, dict) or parsed.get("ok") is not True:
        return PairResult("failed", status=status)
    if parsed.get("ignored") is True:
        return PairResult("failed", status=status)
    token = parsed.get("token")
    instance = parsed.get("instance")
    if not isinstance(token, str) or not token.strip():
        return PairResult("failed", status=status)
    return PairResult(
        "paired",
        token=token.strip(),
        instance=instance.strip() if isinstance(instance, str) else "",
        status=status,
    )
