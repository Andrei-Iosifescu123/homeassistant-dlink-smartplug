"""Switch platform for D-Link Smart Plug."""
import asyncio
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_NAME
from .coordinator import DLinkSmartPlugDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up D-Link Smart Plug switches from a config entry."""
    coordinator: DLinkSmartPlugDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Determine number of sockets based on model
    model = entry.data.get("model", "W245")
    num_sockets = 4 if model == "W245" else 1
    
    # Get device name
    device_name = entry.data.get(CONF_NAME, "D-Link Smart Plug")
    
    entities = []
    for socket_num in range(1, num_sockets + 1):
        entities.append(
            DLinkSmartPlugSwitch(coordinator, socket_num, device_name)
        )
    
    async_add_entities(entities)


class DLinkSmartPlugSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a D-Link Smart Plug socket."""

    def __init__(
        self,
        coordinator: DLinkSmartPlugDataUpdateCoordinator,
        socket_num: int,
        device_name: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._socket_num = socket_num
        self._attr_name = f"{device_name} Socket {socket_num}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_socket_{socket_num}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Entity is available unless coordinator has no data (connection failed)
        # Even if state is unknown (None response), entity stays available
        return self.coordinator.data is not None
    
    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on, None if state is unknown."""
        if not self.coordinator.data:
            return None  # No data = unknown
        
        if "sockets" not in self.coordinator.data:
            return None  # No socket data = unknown
        
        # Check if state is marked as unknown (invalid response format)
        if self.coordinator.data.get("unknown", False):
            # For unknown state, return last known state if we have it
            # This keeps entity available but shows last known state
            sockets = self.coordinator.data.get("sockets", {})
            if self._socket_num in sockets:
                # Return last known state (entity stays available, shows last state)
                return sockets[self._socket_num]
            # No last known state - return None (will show as unavailable in UI)
            # But entity itself is still available
            return None
        
        # Normal case: return the socket state
        return self.coordinator.data["sockets"].get(self._socket_num, False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the socket on."""
        # Send command and get response (which contains the new state)
        response = await self.coordinator.client.async_set_socket(self._socket_num, True)
        
        # Update local state immediately from response if available
        if response and isinstance(response, dict) and 'setting' in response:
            try:
                new_value = response['setting'][0]['metadata']['value']
                new_state = new_value == 1
                # Update coordinator data immediately with the actual device state
                if self.coordinator.data and 'sockets' in self.coordinator.data:
                    self.coordinator.data['sockets'][self._socket_num] = new_state
                    # Notify listeners of the update
                    self.coordinator.async_update_listeners()
            except (KeyError, IndexError, TypeError):
                pass
        
        # Also refresh to ensure we have the latest state
        await self.coordinator.async_request_refresh()
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the socket off."""
        # Send command and get response (which contains the new state)
        response = await self.coordinator.client.async_set_socket(self._socket_num, False)
        
        # Update local state immediately from response if available
        if response and isinstance(response, dict) and 'setting' in response:
            try:
                new_value = response['setting'][0]['metadata']['value']
                new_state = new_value == 1
                # Update coordinator data immediately with the actual device state
                if self.coordinator.data and 'sockets' in self.coordinator.data:
                    self.coordinator.data['sockets'][self._socket_num] = new_state
                    # Notify listeners of the update
                    self.coordinator.async_update_listeners()
            except (KeyError, IndexError, TypeError):
                pass
        
        # Also refresh to ensure we have the latest state
        await self.coordinator.async_request_refresh()

