# D-Link Smart Plug Home Assistant Integration

Home Assistant custom integration for D-Link DSP-W245 and DSP-W115 smart plugs.

## Installation

### Manual Installation

1. Copy the `custom_components/dlink_smartplug` folder to your Home Assistant `custom_components` directory.
2. Ensure `dspW245.py` is in the parent directory of `custom_components` (the project root).
3. Restart Home Assistant.
4. Go to Settings → Devices & Services → Add Integration.
5. Search for "D-Link Smart Plug" and follow the setup wizard.

### Configuration

The integration uses a config flow, so you can set it up through the UI:

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "D-Link Smart Plug"
4. Enter:
   - **IP Address or Hostname**: The IP address of your smart plug (e.g., `192.168.0.20`)
   - **PIN Code**: The PIN code from the back of the device
   - **Device Name**: A friendly name for your device (optional, defaults to "D-Link Smart Plug")
   - **Device Model**: Select W245 or W115 (defaults to W245)

## Features

- **Switch Control**: Control each socket individually (4 sockets for W245, 1 for W115)
- **State Querying**: Automatically queries and updates socket states (configurable, default: 5 seconds)
- **Keep Alive**: Maintains connection to the device

## Requirements

- The device must be on the same network as Home Assistant
- The device should not be paired with the mydlink app (use PIN code)
- Python 3.8 or higher

## Troubleshooting

### Connection Issues

If you're having trouble connecting:
1. Verify the IP address is correct and the device is on the network
2. Check that the PIN code is correct (6 digits, usually on the back of the device)
3. Ensure the device is not paired with the mydlink app
4. Check Home Assistant logs for detailed error messages

### Device Not Found

If the device is not found during setup:
- Make sure the device is powered on and connected to WiFi
- Try pinging the device from Home Assistant: `ping <device_ip>`
- Verify the device model is correct (W245 or W115)

## Support

For issues and feature requests, please open an issue on the GitHub repository.

