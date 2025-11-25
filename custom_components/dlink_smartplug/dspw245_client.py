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
        # Lock to prevent concurrent commands to the same socket
        self._command_locks = {}  # socket_num -> asyncio.Lock
        
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
        await self.async_ensure_connected()
        plug = self._get_plug()
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, plug.get_socket_states, socket)
            if result is None:
                # Log the actual response that was received
                import json
                last_response = getattr(plug, '_last_get_setting_response', None)
                if last_response:
                    _LOGGER.warning(
                        "get_socket_states returned None. "
                        "Device response was: %s",
                        json.dumps(last_response, indent=2)
                    )
                else:
                    _LOGGER.warning(
                        "get_socket_states returned None. "
                        "No response stored for debugging."
                    )
            return result
        except Exception as e:
            _LOGGER.warning("Error getting socket states, reconnecting: %s", e)
            await self.async_reconnect()
            # Retry once after reconnection
            result = await loop.run_in_executor(None, plug.get_socket_states, socket)
            if result is None:
                import json
                last_response = getattr(plug, '_last_get_setting_response', None)
                if last_response:
                    _LOGGER.warning(
                        "get_socket_states returned None after reconnection. "
                        "Device response was: %s",
                        json.dumps(last_response, indent=2)
                    )
                else:
                    _LOGGER.warning(
                        "get_socket_states returned None after reconnection. "
                        "Device may be returning invalid response format."
                    )
            return result
    
    async def async_set_socket(self, socket: int, on: bool):
        """Set socket state with locking to prevent concurrent commands.
        
        Returns:
            dict: Response from device, or None on error
            The response includes the new state in setting[0].metadata.value
        """
        # Get or create lock for this socket
        if socket not in self._command_locks:
            self._command_locks[socket] = asyncio.Lock()
        
        # Acquire lock to prevent concurrent commands to same socket
        async with self._command_locks[socket]:
            await self.async_ensure_connected()
            plug = self._get_plug()
            loop = asyncio.get_event_loop()
            try:
                # Send command and wait for completion
                result = await loop.run_in_executor(None, plug.set_socket, socket, on)
                
                # Verify command succeeded (check response for error code)
                if result and isinstance(result, dict):
                    if result.get('code', 0) != 0:
                        error_msg = result.get('message', 'Unknown error')
                        raise Exception(f"Device returned error: {error_msg}")
                    
                    # Response contains the new state - we can use this!
                    # result['setting'][0]['metadata']['value'] contains 1 (ON) or 0 (OFF)
                    _LOGGER.debug("Command successful, new state: %s", 
                                 result.get('setting', [{}])[0].get('metadata', {}).get('value'))
                
                return result
            except Exception as e:
                _LOGGER.warning("Error setting socket state, reconnecting: %s", e)
                await self.async_reconnect()
                # Retry once after reconnection
                result = await loop.run_in_executor(None, plug.set_socket, socket, on)
                if result and isinstance(result, dict):
                    if result.get('code', 0) != 0:
                        error_msg = result.get('message', 'Unknown error')
                        raise Exception(f"Device returned error after reconnect: {error_msg}")
                return result
    
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
    
    def _is_connection_alive(self) -> bool:
        """Check if the connection is still alive."""
        if not self._plug:
            return False
        if not hasattr(self._plug, 'socket'):
            return False
        if self._plug.socket is None:
            return False
        try:
            # Check if socket is still connected by trying to get its fileno
            # If socket is closed, this will raise an exception
            self._plug.socket.fileno()
            return True
        except (OSError, AttributeError, ValueError):
            return False
    
    async def async_ensure_connected(self):
        """Ensure connection is alive, reconnect if needed."""
        if not self._is_connection_alive():
            _LOGGER.debug("Connection lost, reconnecting...")
            await self.async_reconnect()
        return self._plug
    
    async def async_reconnect(self):
        """Reconnect to the device."""
        _LOGGER.info("Reconnecting to device at %s", self.host)
        # Close existing connection if any
        if self._plug:
            try:
                await self.async_close()
            except Exception:
                pass
        
        # Reset plug to force new connection
        self._plug = None
        self._device_id = None
        
        # Create new connection
        await self.async_connect()
        await self.async_login()
        _LOGGER.info("Successfully reconnected to device")
    
    async def async_close(self):
        """Close the connection."""
        if self._plug:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._plug.close)
            except Exception as e:
                _LOGGER.debug("Error closing connection: %s", e)
            finally:
                self._plug = None

