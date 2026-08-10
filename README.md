# QuinLED Firmware Updater

A small Home Assistant custom integration that adds a proper **Install** update
button for QuinLED boards running the [QuinLED-Firmware](https://github.com/intermittech/QuinLED-Firmware)
WLED fork.

## Why this exists

The core `wled` integration already gives every QuinLED board an `update`
entity — but it points at *vanilla* upstream WLED, which is the wrong
firmware for these boards. This integration adds a second, correct `update`
entity per device (merged onto the same device page) that flashes the
matching asset from the QuinLED-Firmware GitHub releases instead.

## Requirements

- The device must already be set up via HA's core **WLED** integration.

## What it does automatically

- Discovers every device attached to the `wled` integration on every refresh
  (default hourly) — add a new QuinLED board through the normal WLED
  integration flow and its update entity appears here with **no
  configuration needed**.
- Polls the QuinLED-Firmware GitHub releases for the latest version.
- On **Install**, resolves the correct release asset for that board, downloads
  it, and uploads it to the device's OTA endpoint.

## Installation (HACS custom repository)

1. HACS → the "⋮" menu (top right) → **Custom repositories**.
2. Repository: `https://github.com/TheFehr/ha-quinled-updater`, Category: **Integration**.
3. Install "QuinLED Firmware Updater", restart Home Assistant.
4. Settings → Devices & Services → **Add Integration** → "QuinLED Firmware Updater".

## Known boards

| Self-reported model | Release asset used |
|---|---|
| `Dig-Quad-V3` | `Dig-Quad-V3` (used as-is) |
| `An-Penta-Mini` | `An-Penta-Mini` (used as-is) |
| `Dig2Go-Audioreactive` | `Dig2Go-Audioreactive` (used as-is) |
| `Dig-Uno-Audioreactive` | `Dig-Uno-V3-AEplus` (legacy name, mapped) |

Most boards' self-reported model name matches a release asset name exactly
and need no special handling. A few older firmware builds report a legacy
name that no longer matches — those need a one-line entry in
`MODEL_ASSET_MAP` in
[`custom_components/quinled_updater/const.py`](custom_components/quinled_updater/const.py).

If a device's Install button fails with "No matching QuinLED-Firmware release
asset", the error message names the model it tried and lists every asset
actually available in the latest release — add a mapping entry for it and
reload the integration.

## License

MIT
