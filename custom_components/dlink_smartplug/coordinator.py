"""Data update coordinator for D-Link Smart Plug."""
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_SCAN_INTERVAL
from .dspw245_client import DLinkSmartPlugClient

_LOGGER = logging.getLogger(__name__)


class DLinkSmartPlugDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the D-Link Smart Plug."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.entry = entry
        self.client = DLinkSmartPlugClient(
            host=entry.data["host"],
            pin=entry.data["pin"],
            model=entry.data.get("model", "W245")
        )
        
        # Get scan interval from config, default to 5 seconds
        scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self):
        """Fetch data from the device."""
        try:
            # Ensure connection
            if not self.client._plug:
                await self.client.async_connect()
                await self.client.async_login()
            
            # Get socket states
            socket_states = await self.client.async_get_socket_states(socket=-1)
            
            # Send keep alive
            await self.client.async_keep_alive()
            
            if socket_states is None:
                raise UpdateFailed("Failed to get socket states")
            
            return {
                "sockets": socket_states,
                "device_id": self.client.get_device_id(),
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err
    
    async def async_shutdown(self):
        """Shutdown the coordinator and close connections."""
        await self.client.async_close()
        await super().async_shutdown()

