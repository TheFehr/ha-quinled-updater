"""Constants for the QuinLED Firmware Updater integration."""

from datetime import timedelta

DOMAIN = "quinled_updater"

WLED_DOMAIN = "wled"

GITHUB_REPO = "intermittech/QuinLED-Firmware"
GITHUB_API_LATEST_RELEASE_URL = (
    f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
)
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
GITHUB_ASSET_DOWNLOAD_URL = (
    f"https://github.com/{GITHUB_REPO}/releases/download/v{{version}}/{{filename}}"
)

# Firmware asset filenames are always prefixed "WLED_", regardless of the
# device's self-reported `brand` (QuinLED firmware reports brand "QuinLED",
# but release assets are still named WLED_<version>_<asset>.bin).
ASSET_PREFIX = "WLED"

# Some devices self-report a `release`/`product` name (via /json/info) that
# no longer matches a real release asset - e.g. a board still running old
# firmware that predates a board rename. Map those known cases here. If a
# device's name isn't in this map, its raw name is tried as-is first.
MODEL_ASSET_MAP: dict[str, str] = {
    "Dig-Uno-Audioreactive": "Dig-Uno-V3-AEplus",
    "Dig-Quad-Audioreactive": "Dig-Quad-V3",
}

SCAN_INTERVAL = timedelta(hours=1)

OTA_UPLOAD_FIELD_NAME = "file"
OTA_PATH = "/update"

# The device's own /update form posts this alongside the file (as a hidden
# input toggled by an "Ignore firmware validation" checkbox) to bypass its
# release-name safety check. Not a persistent device setting - must be sent
# with every request that needs it. WLED/QuinLED firmware refuses an OTA
# upload whose embedded release name doesn't match its own currently
# installed release name; that's expected and desired for boards not in
# MODEL_ASSET_MAP, so this is only sent when we've deliberately mapped a
# known legacy/renamed board name (see async_install in update.py).
OTA_SKIP_VALIDATION_FIELD_NAME = "skipValidation"
