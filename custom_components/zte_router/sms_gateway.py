"""Shared SMS send logic for the service and notify platform."""

from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import ROUTER_TYPE_MC888, ROUTER_TYPE_MC889
from .coordinators import extract_json
from .router_backend import run_router_commands

_LOGGER = logging.getLogger(__name__)

EVENT_SMS_SENT = "zte_router_sms_sent"


def resolve_phone_number(
    *,
    phone: str | None = None,
    phone_number: str | None = None,
    target: Any = None,
    default_phone: str | None = None,
) -> str:
    """Resolve the destination number from service/notify call parameters."""
    for candidate in (phone, phone_number):
        if candidate and str(candidate).strip():
            return str(candidate).strip()

    if target is not None:
        if isinstance(target, (list, tuple)):
            for item in target:
                if item and str(item).strip():
                    return str(item).strip()
        elif str(target).strip():
            return str(target).strip()

    if default_phone and str(default_phone).strip():
        return str(default_phone).strip()

    raise HomeAssistantError(
        "Provide a destination phone number via phone_number, phone, or target."
    )


def validate_sms_send_result(result: Any) -> dict[str, Any]:
    """Validate router SMS send output and return a normalized result dict."""
    if result is None:
        raise HomeAssistantError("No result returned for send SMS command")

    if isinstance(result, str):
        if "not provided" in result.lower() or "not supported" in result.lower():
            raise HomeAssistantError(result)
        raise HomeAssistantError(f"Unexpected SMS response: {result}")

    if isinstance(result, dict):
        if result.get("error"):
            raise HomeAssistantError(f"Failed to send SMS: {result['error']}")

        command_status = result.get("command_status")
        if isinstance(command_status, dict):
            status = command_status.get("status")
            if status == "failed":
                raise HomeAssistantError(
                    f"Router reported SMS send failure: {command_status.get('details')}"
                )
            if status == "timeout":
                raise HomeAssistantError(
                    "Timed out waiting for the router to confirm SMS delivery"
                )
            if status != "success":
                raise HomeAssistantError(
                    f"Unexpected SMS command status: {status or command_status}"
                )

        request = result.get("request")
        if isinstance(request, dict) and request.get("error"):
            raise HomeAssistantError(f"Failed to send SMS: {request['error']}")

        return {"success": True, "raw": result}

    if isinstance(result, int):
        if 200 <= result < 300:
            return {"success": True, "http_status": result}
        raise HomeAssistantError(f"Router returned HTTP status {result} while sending SMS")

    raise HomeAssistantError(f"Unexpected SMS response type: {type(result).__name__}")


async def async_send_custom_sms(
    hass: HomeAssistant,
    *,
    router_type: str,
    router_ip: str,
    router_password: str,
    username: str | None,
    phone: str,
    message: str,
) -> dict[str, Any]:
    """Send a custom SMS through the configured router backend."""
    text = message.strip()
    if not text:
        raise HomeAssistantError("SMS message cannot be empty")

    try:
        raw = await hass.async_add_executor_job(
            run_router_commands,
            router_type,
            router_ip,
            router_password,
            username,
            "8",
            phone,
            text,
        )
    except HomeAssistantError:
        raise
    except Exception as err:
        raise HomeAssistantError(f"Failed to send SMS: {err}") from err

    try:
        parsed = json.loads(extract_json(raw))
    except Exception as err:
        raise HomeAssistantError(f"Unexpected response from router: {raw}") from err

    result = parsed.get("8")
    if result is None:
        raise HomeAssistantError(f"No result returned for send SMS command: {parsed}")

    validated = validate_sms_send_result(result)
    _LOGGER.info("SMS sent to %s via router %s", phone, router_ip)
    return validated


def router_username_for_entry(merged: dict[str, Any], router_type: str) -> str | None:
    """Return the router username when the model requires one."""
    if router_type in (ROUTER_TYPE_MC888, ROUTER_TYPE_MC889):
        return merged.get("router_username")
    return None
