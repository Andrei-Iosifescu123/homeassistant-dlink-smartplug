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
        
        # Track consecutive failures (only go unavailable after 3 failures)
        self._consecutive_failures = 0
        self._last_known_data = None
        self._failure_history = []  # Store last 3 errors for logging
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self):
        """Fetch data from the device."""
        try:
            # Ensure connection is alive (will reconnect if needed)
            await self.client.async_ensure_connected()
            
            # Get socket states
            socket_states = await self.client.async_get_socket_states(socket=-1)
            
            # Send keep alive
            try:
                await self.client.async_keep_alive()
            except Exception as e:
                _LOGGER.debug("Keep alive failed, may need reconnection: %s", e)
                # If keep alive fails, try to reconnect
                await self.client.async_reconnect()
                # Retry getting socket states after reconnection
                socket_states = await self.client.async_get_socket_states(socket=-1)
            
            # Handle None response (invalid format) - mark as Unknown, not Unavailable
            if socket_states is None:
                # The client wrapper already logs the actual response
                # Return last known state to keep entity available but mark as unknown
                _LOGGER.warning(
                    "Device returned invalid response format. "
                    "Marking socket states as unknown (entity stays available)."
                )
                # Return last known state if available, otherwise empty
                # This keeps the entity available but indicates state is unknown
                unknown_sockets = {}
                if self._last_known_data and "sockets" in self._last_known_data:
                    # Preserve last known states
                    unknown_sockets = self._last_known_data["sockets"].copy()
                
                return {
                    "sockets": unknown_sockets,  # Last known states (or empty if none)
                    "device_id": self.client.get_device_id(),
                    "unknown": True,  # Flag to indicate unknown state
                }
            
            # Success! Reset failure counter and update last known data
            self._consecutive_failures = 0
            data = {
                "sockets": socket_states,
                "device_id": self.client.get_device_id(),
                "unknown": False,
            }
            self._last_known_data = data
            return data
            
        except Exception as err:
            # Check if this is a connection error (should mark unavailable)
            # vs other errors (could be temporary)
            is_connection_error = isinstance(err, (
                ConnectionError, 
                TimeoutError, 
                OSError,
                # Also check error message for connection-related errors
            )) or "connection" in str(err).lower() or "timeout" in str(err).lower()
            
            # Increment failure counter
            self._consecutive_failures += 1
            
            # Store error in history (keep last 3)
            error_info = {
                "failure": self._consecutive_failures,
                "error": str(err),
                "error_type": type(err).__name__,
                "is_connection_error": is_connection_error
            }
            self._failure_history.append(error_info)
            if len(self._failure_history) > 3:
                self._failure_history.pop(0)
            
            _LOGGER.warning(
                "Error communicating with device (failure %d/3): %s", 
                self._consecutive_failures, 
                err
            )
            
            # Try to reconnect and retry once
            try:
                await self.client.async_reconnect()
                socket_states = await self.client.async_get_socket_states(socket=-1)
                if socket_states is not None:
                    # Success on retry! Reset counter and history
                    self._consecutive_failures = 0
                    self._failure_history = []
                    data = {
                        "sockets": socket_states,
                        "device_id": self.client.get_device_id(),
                        "unknown": False,
                    }
                    self._last_known_data = data
                    _LOGGER.info("Device reconnected successfully after %d failures", 
                                len(self._failure_history))
                    return data
            except Exception as retry_err:
                _LOGGER.debug("Retry after reconnect also failed: %s", retry_err)
                # Add retry error to history
                error_info["retry_error"] = str(retry_err)
                # Check if retry error is also a connection error
                is_retry_connection_error = isinstance(retry_err, (
                    ConnectionError, TimeoutError, OSError
                )) or "connection" in str(retry_err).lower() or "timeout" in str(retry_err).lower()
                error_info["retry_is_connection_error"] = is_retry_connection_error
            
            # Only go unavailable after 3 consecutive CONNECTION failures
            # If it's a connection error and we've failed 3 times, mark unavailable
            if self._consecutive_failures >= 3 and is_connection_error:
                # Log detailed error information
                _LOGGER.error(
                    "Device unavailable after %d consecutive connection failures. "
                    "Error history: %s. "
                    "Last error: %s (type: %s)", 
                    self._consecutive_failures,
                    [f"{e['failure']}: {e['error_type']} - {e['error']}" for e in self._failure_history],
                    err,
                    type(err).__name__
                )
                # Log full exception traceback for debugging
                _LOGGER.exception(
                    "Full exception traceback for unavailable device:"
                )
                raise UpdateFailed(
                    f"Device unavailable after 3 consecutive connection failures. "
                    f"Errors: {[e['error'] for e in self._failure_history]}. "
                    f"Last error: {err}"
                ) from err
            
            # For non-connection errors or < 3 failures, return unknown state
            # Return last known data to keep entity available but in unknown state
            if self._last_known_data is not None:
                _LOGGER.debug(
                    "Using last known data (failure %d/3). Device may be temporarily unreachable.",
                    self._consecutive_failures
                )
                # Mark as unknown
                unknown_data = self._last_known_data.copy()
                unknown_data["unknown"] = True
                return unknown_data
            
            # If we have no last known data and haven't failed 3 times yet,
            # return empty data to keep entity available but in unknown state
            _LOGGER.debug(
                "No previous data available (failure %d/3). Entity will show unknown state.",
                self._consecutive_failures
            )
            return {
                "sockets": {},
                "device_id": self.client.get_device_id(),
                "unknown": True,
            }
    
    async def async_shutdown(self):
        """Shutdown the coordinator and close connections."""
        await self.client.async_close()
        await super().async_shutdown()

