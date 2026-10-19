"""Minimal Azure-safe Moomoo REST client.

This module deliberately implements only the *simulated trading* endpoints that
Kallisto needs for broker-paper validation. It contains no real-money order
endpoint.

Authentication follows Moomoo's AppKey signing scheme for server-side jobs:
timestamp + method + path + query + SHA256(body), signed with Ed25519 or
RSA-SHA256.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any, Iterable

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa


DEFAULT_BASE_URL = "https://webapi.moomoo.com"


class MoomooRestError(RuntimeError):
    pass


def _compact_json_bytes(payload: dict | None) -> bytes:
    if payload is None:
        return b""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def build_signing_string(
    timestamp_ms: int,
    method: str,
    path: str,
    query_string: str = "",
    body_bytes: bytes = b"",
) -> str:
    body_part = hashlib.sha256(body_bytes).hexdigest() if body_bytes else ""
    return "\n".join(
        [
            str(int(timestamp_ms)),
            method.upper(),
            path,
            query_string,
            body_part,
        ]
    )


@dataclass(frozen=True)
class MoomooCredentials:
    app_key: str
    private_key_pem: str
    algorithm: str = "ED25519"

    @classmethod
    def from_env(cls) -> "MoomooCredentials":
        app_key = os.environ.get("MOOMOO_APP_KEY", "").strip()
        private_key = os.environ.get("MOOMOO_PRIVATE_KEY_PEM", "").strip()
        algorithm = os.environ.get("MOOMOO_SIGN_ALGORITHM", "ED25519").strip().upper()
        if not app_key:
            raise MoomooRestError("MOOMOO_APP_KEY is missing.")
        if not private_key:
            raise MoomooRestError("MOOMOO_PRIVATE_KEY_PEM is missing.")
        if "\\n" in private_key and "-----BEGIN" in private_key:
            private_key = private_key.replace("\\n", "\n")
        if algorithm not in {"ED25519", "RSA-SHA256"}:
            raise MoomooRestError(f"Unsupported MOOMOO_SIGN_ALGORITHM: {algorithm}")
        return cls(app_key=app_key, private_key_pem=private_key, algorithm=algorithm)


class MoomooRestClient:
    """Authenticated Moomoo REST client restricted to simulated trading."""

    def __init__(
        self,
        credentials: MoomooCredentials,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = 12.0,
    ) -> None:
        self.credentials = credentials
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        self._private_key = self._load_private_key()

    @classmethod
    def from_env(cls) -> "MoomooRestClient":
        return cls(
            MoomooCredentials.from_env(),
            base_url=os.environ.get("MOOMOO_API_BASE_URL", DEFAULT_BASE_URL),
            timeout_seconds=float(os.environ.get("MOOMOO_HTTP_TIMEOUT_SECONDS", "12")),
        )

    def _load_private_key(self):
        key = serialization.load_pem_private_key(
            self.credentials.private_key_pem.encode("utf-8"),
            password=None,
        )
        if self.credentials.algorithm == "ED25519" and not isinstance(key, ed25519.Ed25519PrivateKey):
            raise MoomooRestError("Configured ED25519 but private key is not an Ed25519 key.")
        if self.credentials.algorithm == "RSA-SHA256" and not isinstance(key, rsa.RSAPrivateKey):
            raise MoomooRestError("Configured RSA-SHA256 but private key is not an RSA key.")
        return key

    def _sign(self, signing_string: str) -> str:
        message = signing_string.encode("utf-8")
        if self.credentials.algorithm == "ED25519":
            signature = self._private_key.sign(message)
        else:
            signature = self._private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(signature).decode("ascii")

    def _headers(
        self,
        *,
        method: str,
        path: str,
        query_string: str,
        body_bytes: bytes,
        timestamp_ms: int,
    ) -> dict[str, str]:
        signing_string = build_signing_string(
            timestamp_ms,
            method,
            path,
            query_string=query_string,
            body_bytes=body_bytes,
        )
        return {
            "X-Api-Key": self.credentials.app_key,
            "X-Timestamp": str(timestamp_ms),
            "X-Nonce": uuid.uuid4().hex,
            "Authorization": self._sign(signing_string),
            "Accept": "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Iterable[tuple[str, str | int | float]] | None = None,
        body: dict | None = None,
    ) -> dict:
        if not path.startswith("/api/v1.0/sim-trade/"):
            raise MoomooRestError(
                f"Safety block: MoomooRestClient only permits simulated-trading paths, got {path}"
            )

        method = method.upper()
        query_items = list(query or [])
        query_string = urllib.parse.urlencode(query_items)
        body_bytes = _compact_json_bytes(body)
        timestamp_ms = int(time.time() * 1000)
        headers = self._headers(
            method=method,
            path=path,
            query_string=query_string,
            body_bytes=body_bytes,
            timestamp_ms=timestamp_ms,
        )
        if body is not None:
            headers["Content-Type"] = "application/json"

        url = f"{self.base_url}{path}"
        if query_string:
            url += "?" + query_string
        req = urllib.request.Request(
            url,
            data=body_bytes if body is not None else None,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise MoomooRestError(f"Moomoo HTTP {exc.code}: {detail[:500]}") from exc
        except urllib.error.URLError as exc:
            raise MoomooRestError(f"Moomoo network error: {exc}") from exc

        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise MoomooRestError("Moomoo returned non-JSON data.") from exc

        ret_code = payload.get("ret_code", payload.get("code", 0))
        if ret_code not in (0, "0", None):
            raise MoomooRestError(
                f"Moomoo API error {ret_code}: {payload.get('ret_msg') or payload.get('msg') or payload}"
            )
        return payload.get("data", payload)

    # ---- Simulated trading only -------------------------------------------------

    def simulated_accounts(self) -> list[dict]:
        data = self.request("GET", "/api/v1.0/sim-trade/accounts")
        return list(data.get("accounts") or [])

    def cash_info(self, acc_id: str) -> dict:
        return self.request("GET", f"/api/v1.0/sim-trade/{acc_id}/cash-info")

    def positions(self, acc_id: str, *, market: int | None = None) -> list[dict]:
        query = [] if market is None else [("market", int(market))]
        data = self.request("GET", f"/api/v1.0/sim-trade/{acc_id}/positions", query=query)
        return list(data.get("positions") or [])

    def orders(self, acc_id: str) -> list[dict]:
        data = self.request("GET", f"/api/v1.0/sim-trade/{acc_id}/orders")
        return list(data.get("orders") or [])

    def max_buy_sell(
        self,
        acc_id: str,
        *,
        symbol: str,
        order_type: int = 3,
        price: float | None = None,
    ) -> dict:
        query: list[tuple[str, str | int | float]] = [
            ("symbol", symbol),
            ("order_type", int(order_type)),
        ]
        if price is not None:
            query.append(("price", str(price)))
        return self.request(
            "GET",
            f"/api/v1.0/sim-trade/{acc_id}/max-buy-sell",
            query=query,
        )

    def place_order(
        self,
        acc_id: str,
        *,
        market: int,
        symbol: str,
        order_side: int,
        qty: int,
        order_type: int = 3,
        price: float | None = None,
        text: str = "",
        include_extended_hours: bool = False,
    ) -> dict:
        body: dict[str, Any] = {
            "market": int(market),
            "symbol": symbol,
            "order_type": int(order_type),
            "order_side": int(order_side),
            "qty": str(int(qty)),
            "text": text[:100],
            "order_trade_time_type": 2 if include_extended_hours else 1,
        }
        if price is not None:
            body["price"] = str(float(price))
        return self.request(
            "POST",
            f"/api/v1.0/sim-trade/{acc_id}/orders",
            body=body,
        )

    def cancel_order(self, acc_id: str, order_id: str) -> dict:
        return self.request(
            "POST",
            f"/api/v1.0/sim-trade/{acc_id}/orders/{order_id}/cancel",
            body={},
        )
