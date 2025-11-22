# D-Link Smart Plug Home Assistant Integration

[![GitHub release](https://img.shields.io/github/release/Andrei-Iosifescu123/homeassistant-dlink-smartplug.svg)](https://github.com/Andrei-Iosifescu123/homeassistant-dlink-smartplug/releases)
[![License](https://img.shields.io/github/license/Andrei-Iosifescu123/homeassistant-dlink-smartplug.svg)](LICENSE)

A Home Assistant custom integration for controlling D-Link DSP-W245 (4 sockets) and DSP-W115 (1 socket) smart plugs.

## Features

- ✅ **Full socket control** - Control each socket individually (4 sockets for W245, 1 for W115)
- ✅ **Real-time state updates** - Automatically queries and updates socket states
- ✅ **Configurable polling** - Adjustable update interval (1-300 seconds, default: 5s)
- ✅ **UI-based setup** - Easy configuration through Home Assistant UI (no YAML editing)
- ✅ **Persistent connection** - Maintains WebSocket connection with keep-alive
- ✅ **Secure communication** - SSL/TLS encrypted communication
- ✅ **Auto-reconnection** - Handles connection drops gracefully

## Supported Devices

- **D-Link DSP-W245** - 4 individually controllable sockets
- **D-Link DSP-W115** - 1 controllable socket

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to Integrations
3. Click the three dots (⋮) → Custom repositories
4. Add repository: `https://github.com/Andrei-Iosifescu123/homeassistant-dlink-smartplug`
5. Category: Integration
6. Click Install
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/dlink_smartplug` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to **Settings** → **Devices & Services** → **Add Integration**
4. Search for "D-Link Smart Plug" and follow the setup wizard

## Configuration

The integration uses a config flow, so you can set it up through the UI:

1. Go to **Settings** → **Devices & Services**
2. Click **"+ ADD INTEGRATION"**
3. Search for **"D-Link Smart Plug"**
4. Enter:
   - **IP Address or Hostname**: The IP address of your smart plug (e.g., `192.168.0.20`)
   - **PIN Code**: The 6-digit PIN code from the back of the device
   - **Device Name**: A friendly name for your device (optional)
   - **Device Model**: Select W245 or W115 (defaults to W245)
   - **Update Interval**: How often to poll for state updates (default: 5 seconds)

## Requirements

- Home Assistant 2023.1 or later
- The device must be on the same network as Home Assistant
- The device should **not** be paired with the mydlink app (use PIN code)
- Python 3.8 or higher

## Usage

After installation, you'll have switch entities for each socket:

- `switch.dlink_smart_plug_socket_1`
- `switch.dlink_smart_plug_socket_2`
- `switch.dlink_smart_plug_socket_3`
- `switch.dlink_smart_plug_socket_4` (W245 only)

You can control these switches from the Home Assistant UI, use them in automations, or control them via the API.

## Troubleshooting

### Integration doesn't appear
- Check that all files are in `custom_components/dlink_smartplug/`
- Restart Home Assistant completely
- Check Home Assistant logs for errors

### "Cannot connect" error
- Verify the IP address is correct (ping the device)
- Check the PIN code is correct (6 digits)
- Ensure device is powered on and connected to WiFi
- Make sure device is **not** paired with the mydlink app

### Socket states not updating
- Check Home Assistant logs for errors
- Verify network connectivity
- Try increasing the update interval if network is slow

## Credits

This integration is based on and extends the work of:

- **Original Library**: [dspW245](https://github.com/jonassjoh/dspW245) by [@jonassjoh](https://github.com/jonassjoh) (Jonas Johansson)
- **Contributions**: [@afoteas](https://github.com/afoteas) for bug fixes and improvements
- **Node.js Reference**: [dlinkWebSocketClient](https://github.com/Garfonso/dlinkWebSocketClient) by [@Garfonso](https://github.com/Garfonso)

The Home Assistant integration was created by [@Andrei-Iosifescu123](https://github.com/Andrei-Iosifescu123).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and feature requests, please open an issue on [GitHub](https://github.com/Andrei-Iosifescu123/homeassistant-dlink-smartplug/issues).
=======

- Based on the original [dspW245](https://github.com/jonassjoh/dspW245) library by jonassjoh
- Inspired by the Node.js implementation by [Garfonso](https://github.com/Garfonso/dlinkWebSocketClient)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and feature requests, please open an issue.
