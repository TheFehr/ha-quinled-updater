"""DataUpdateCoordinator for QuinLED Firmware Updater."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, GITHUB_API_LATEST_RELEASE_URL, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuinLEDReleaseData:
    """Latest QuinLED-Firmware GitHub release info."""

    version: str
    asset_filenames: frozenset[str]
    """Exact release asset filenames as published on GitHub, e.g. 'WLED_16.0.1_Dig-Quad-V3.bin'."""


class QuinLEDReleaseCoordinator(DataUpdateCoordinator[QuinLEDReleaseData]):
    """Polls GitHub for the latest QuinLED-Firmware release."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> QuinLEDReleaseData:
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                GITHUB_API_LATEST_RELEASE_URL,
                headers={"Accept": "application/vnd.github+json"},
            ) as response:
                response.raise_for_status()
                payload = await response.json()
        except Exception as err:  # noqa: BLE001 - surfaced via UpdateFailed
            raise UpdateFailed(
                f"Error fetching latest QuinLED-Firmware release from GitHub: {err}"
            ) from err

        tag_name: str = payload["tag_name"]
        version = tag_name.removeprefix("v")
        asset_filenames = frozenset(
            asset["name"] for asset in payload.get("assets", [])
        )

        return QuinLEDReleaseData(version=version, asset_filenames=asset_filenames)
