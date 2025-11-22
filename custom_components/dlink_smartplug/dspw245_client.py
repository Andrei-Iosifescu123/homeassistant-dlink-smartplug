"""Async wrapper for the dspW245 SmartPlug client."""
import asyncio
import logging
from typing import Optional

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class DLinkSmartPlugClient:
    """Async wrapper for SmartPlug client."""
    
    def __init__(self, host: str, pin: str, model: str = "W245"):
        """Initialize the client."""
        self.host = host
        self.pin = pin
        self.model = model
        self._plug = None
        self._device_id = None
        
    def _get_plug(self):
        """Get or create the SmartPlug instance."""
        if self._plug is None:
            from .dspW245 import SmartPlug
            self._plug = SmartPlug(self.host, self.pin, model=self.model, verbose=0)
        return self._plug
    
    async def async_connect(self):
        """Connect to the device (connection happens in __init__)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._get_plug)
    
    async def async_login(self):
        """Login to the device (login happens in __init__)."""
        plug = self._get_plug()
        if hasattr(plug, 'obj') and 'device_id' in plug.obj:
            self._device_id = plug.obj['device_id']
        else:
            await self.async_get_device_status()
            if hasattr(plug, 'obj') and 'device_id' in plug.obj:
                self._device_id = plug.obj['device_id']
    
    def get_device_id(self) -> Optional[str]:
        """Get the device ID."""
        if self._device_id:
            return self._device_id
        plug = self._get_plug()
        if hasattr(plug, 'obj') and 'device_id' in plug.obj:
            return plug.obj['device_id']
        return None
    
    async def async_get_socket_states(self, socket: int = -1):
        """Get socket states."""
        plug = self._get_plug()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, plug.get_socket_states, socket)
    
    async def async_set_socket(self, socket: int, on: bool):
        """Set socket state."""
        plug = self._get_plug()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, plug.set_socket, socket, on)
    
    async def async_get_device_status(self):
        """Get device status."""
        plug = self._get_plug()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, plug.device_status)
    
    async def async_keep_alive(self):
        """Send keep alive."""
        plug = self._get_plug()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, plug.keep_alive)
    
    async def async_close(self):
        """Close the connection."""
        if self._plug:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._plug.close)
            self._plug = None

