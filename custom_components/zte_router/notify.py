"""Notify platform exposing an SMS gateway for Home Assistant automations."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.notify import NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .sms_gateway import EVENT_SMS_SENT, async_send_custom_sms, resolve_phone_number, router_username_for_entry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SMS gateway notify entity for a router config entry."""
    merged = {**config_entry.data, **config_entry.options}
    default_phone = merged.get("phone_number", "")
    async_add_entities(
        [ZTERouterSmsGatewayNotify(hass, config_entry, default_phone)],
        update_before_add=False,
    )


class ZTERouterSmsGatewayNotify(NotifyEntity):
    """Send arbitrary SMS messages through the ZTE router."""

    _attr_has_entity_name = True
    _attr_name = "SMS Gateway"
    _attr_icon = "mdi:message-text"

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        default_phone: str,
    ) -> None:
        """Initialize the SMS gateway notify entity."""
        self.hass = hass
        self._config_entry = config_entry
        self._default_phone = default_phone
        router_ip = config_entry.data["router_ip"]
        self._attr_unique_id = f"{DOMAIN}_{router_ip}_sms_gateway"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{DOMAIN}_{router_ip}")},
        }

    async def async_send_message(self, message: str, title: str | None = None, **kwargs: Any) -> None:
        """Send a custom SMS using the router modem."""
        merged = {**self._config_entry.data, **self._config_entry.options}
        router_type = merged.get("router_type", "MC801")
        phone = resolve_phone_number(
            phone=kwargs.get("phone"),
            phone_number=kwargs.get("phone_number"),
            target=kwargs.get("target"),
            default_phone=self._default_phone,
        )

        body = message.strip()
        if title:
            body = f"{title.strip()}\n{body}" if body else title.strip()
        if not body:
            raise HomeAssistantError("SMS message cannot be empty")

        result = await async_send_custom_sms(
            self.hass,
            router_type=router_type,
            router_ip=merged["router_ip"],
            router_password=merged["router_password"],
            username=router_username_for_entry(merged, router_type),
            phone=phone,
            message=body,
        )

        self.hass.bus.async_fire(
            EVENT_SMS_SENT,
            {
                "entry_id": self._config_entry.entry_id,
                "phone_number": phone,
                "message": body,
                "result": result,
            },
        )
