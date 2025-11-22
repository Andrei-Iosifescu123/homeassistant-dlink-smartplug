# Repository Structure

This repository follows the standard Home Assistant custom integration structure:

```
homeassistant-dlink-smartplug/
├── README.md                    # Main documentation
├── LICENSE                      # MIT License
├── .gitignore                   # Git ignore rules
└── custom_components/
    └── dlink_smartplug/
        ├── __init__.py          # Integration entry point
        ├── manifest.json        # Integration metadata
        ├── config_flow.py       # UI configuration flow
        ├── const.py             # Constants
        ├── coordinator.py       # Data update coordinator
        ├── dspw245_client.py    # Async wrapper for dspW245
        ├── dspW245.py           # Core library (included)
        ├── switch.py            # Switch platform
        ├── strings.json         # UI strings
        └── README.md            # Integration-specific docs
```

## What to Include

### For Integration-Only Repository (Recommended)

Include only:
- `custom_components/dlink_smartplug/` (entire folder)
- `README.md` (root)
- `LICENSE` (root)
- `.gitignore` (root)

Exclude (via .gitignore):
- `dspW245.py` (root) - already included in integration folder
- `plug_control.py` - CLI tool (separate use case)
- `dlinkWebSocketClient-master/` - reference implementation
- Development docs (HOME_ASSISTANT_SETUP.md, etc.)

### For Full Project Repository

Include everything:
- All integration files
- `dspW245.py` (standalone library)
- `plug_control.py` (CLI tool)
- Reference implementations
- All documentation

## Current Setup

The repository is currently set up as an **integration-only** repository, which is the standard for Home Assistant integrations. This makes it:
- Easy to install via HACS
- Clean and focused
- Follows HA community standards

If you want to include the standalone library and CLI tool, you can:
1. Remove those entries from `.gitignore`
2. Update the README to document all components

