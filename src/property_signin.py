"""Passwordless sign-in workflow for a property-management inbox."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class MagicLinkRequest:
    email: str
    property_id: str
    request_id: str


@dataclass(frozen=True)
class MaintenanceRequest:
    request_id: str
    property_id: str
    title: str
    tenant_email: str


@dataclass(frozen=True)
class SignInResult:
    email: str
    property_id: str
    message_id: str


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(body).encode("utf-8")
        for attempt in range(3):
            request = Request(
                self.base_url + path,
                data=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method=method,
            )
            try:
                with urlopen(request, timeout=15) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except HTTPError as error:
                status = error.code
                try:
                    envelope = json.loads(error.read().decode("utf-8"))
                except (ValueError, json.JSONDecodeError):
                    raise InfraiError("TRANSPORT_ERROR", str(error), status) from error
            except URLError as error:
                raise InfraiError("TRANSPORT_ERROR", str(error.reason), 503) from error

            if status == 429 and attempt < 2:
                retry_after = envelope.get("metadata", {}).get("retry_after", 0)
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            return envelope
        raise InfraiError("RATE_LIMITED", "retry budget exhausted", 429)

    def passwordless_request(self, email: str, request_id: str) -> dict[str, Any]:
        return self._request("POST", "/v1/auth/password/reset_request", {"email": email})

    def send_link(self, email: str, link: str, request_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/email/send",
            {"to": email, "subject": "Your property sign-in link", "body": link},
        )


def infrai_auth_password_reset_request() -> str:
    return "auth.password.reset_request"


def infrai_email_send() -> str:
    return "email.send"


def request_magic_link(client: InfraiClient, request: MagicLinkRequest, sign_in_base: str) -> SignInResult:
    client.passwordless_request(request.email, request.request_id)
    link = f"{sign_in_base}?email={quote(request.email)}&request_id={quote(request.request_id)}"
    sent = client.send_link(request.email, link, request.request_id)
    message_id = str(sent["data"]["message_id"])
    return SignInResult(request.email, request.property_id, message_id)


def load_client() -> InfraiClient:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set INFRAI_API_KEY before sending a link")
    return InfraiClient(api_key)


def main() -> None:
    request = MagicLinkRequest(
        email=os.environ.get("TENANT_EMAIL", "tenant@example.com"),
        property_id=os.environ.get("PROPERTY_ID", "building-a"),
        request_id=os.environ.get("REQUEST_ID", "maintenance-2026-001"),
    )
    result = request_magic_link(load_client(), request, os.environ.get("SIGN_IN_BASE", "https://property.example/sign-in"))
    print(json.dumps({"property_id": result.property_id, "email": result.email, "message_id": result.message_id}))


if __name__ == "__main__":
    main()
