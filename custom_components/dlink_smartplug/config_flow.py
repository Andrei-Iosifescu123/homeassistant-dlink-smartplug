"""Config flow for D-Link Smart Plug integration."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN, DEFAULT_PORT, DEFAULT_MODEL, DEFAULT_SCAN_INTERVAL,
    CONF_HOST, CONF_PIN, CONF_MODEL, CONF_NAME, CONF_SCAN_INTERVAL
)
from .dspw245_client import DLinkSmartPlugClient

import logging

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PIN): str,
        vol.Optional(CONF_NAME, default="D-Link Smart Plug"): str,
        vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): vol.In(["W245", "W115"]),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=300)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Validate the user input allows us to connect."""
    client = DLinkSmartPlugClient(
        host=data[CONF_HOST],
        pin=data[CONF_PIN],
        model=data.get(CONF_MODEL, DEFAULT_MODEL)
    )
    
    try:
        # Try to connect and login
        await client.async_connect()
        await client.async_login()
        
        # Get device info
        device_id = client.get_device_id()
        
        # Close connection
        await client.async_close()
        
        return {"title": data.get(CONF_NAME, f"D-Link {data[CONF_MODEL]}"), "device_id": device_id}
    except Exception as exc:
        raise CannotConnect from exc


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for D-Link Smart Plug."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            # Check if already configured
            await self.async_set_unique_id(info["device_id"])
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

