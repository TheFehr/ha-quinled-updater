"""Update platform for QuinLED Firmware Updater."""

from __future__ import annotations

import logging

import aiohttp

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ASSET_PREFIX,
    DOMAIN,
    GITHUB_ASSET_DOWNLOAD_URL,
    GITHUB_RELEASES_URL,
    MODEL_ASSET_MAP,
    OTA_PATH,
    OTA_UPLOAD_FIELD_NAME,
    WLED_DOMAIN,
)
from .coordinator import QuinLEDReleaseCoordinator

_LOGGER = logging.getLogger(__name__)


def _wled_devices(
    hass: HomeAssistant,
) -> dict[str, tuple[dr.DeviceEntry, ConfigEntry]]:
    """Enumerate every device currently registered to the wled integration.

    Returns device_id -> (device_entry, owning wled ConfigEntry). Re-run on
    every coordinator refresh so newly-added or removed QuinLED/WLED devices
    are picked up automatically, with no config change needed here.

    Deliberately resolved via the entity registry (find any wled-platform
    entity for the config entry, then read *its* device_id) rather than
    device_registry.async_entries_for_config_entry(). The latter reads a
    per-config-entry reverse index that can point at a stale/orphaned
    device_id left behind by a prior device-registry migration (observed on
    a real instance: an empty duplicate device coexisting with the device
    that actually owns all the entities). Entity registry linkage reflects
    what's actually live right now, so it doesn't have that failure mode.
    """
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    result: dict[str, tuple[dr.DeviceEntry, ConfigEntry]] = {}
    for entry in hass.config_entries.async_entries(WLED_DOMAIN):
        device_id: str | None = None
        for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
            if entity.device_id:
                device_id = entity.device_id
                break
        if device_id is None:
            continue
        device = device_registry.async_get(device_id)
        if device is None:
            continue
        result[device.id] = (device, entry)
    return result


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up QuinLED update entities, tracking wled devices dynamically."""
    coordinator: QuinLEDReleaseCoordinator = entry.runtime_data
    known_device_ids: set[str] = set()

    @callback
    def _async_sync_devices() -> None:
        current = _wled_devices(hass)
        new_ids = set(current) - known_device_ids
        removed_ids = known_device_ids - set(current)

        if new_ids:
            async_add_entities(
                QuinLEDUpdateEntity(coordinator, *current[device_id])
                for device_id in new_ids
            )
            known_device_ids.update(new_ids)

        if removed_ids:
            entity_registry = er.async_get(hass)
            for device_id in removed_ids:
                unique_id = f"{DOMAIN}_{device_id}"
                entity_id = entity_registry.async_get_entity_id(
                    "update", DOMAIN, unique_id
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)
            known_device_ids.difference_update(removed_ids)

    entry.async_on_unload(coordinator.async_add_listener(_async_sync_devices))
    _async_sync_devices()


class QuinLEDUpdateEntity(CoordinatorEntity[QuinLEDReleaseCoordinator], UpdateEntity):
    """Update entity that flashes QuinLED-Firmware onto a wled device."""

    _attr_has_entity_name = True
    _attr_name = "QuinLED Firmware"
    _attr_supported_features = UpdateEntityFeature.INSTALL

    def __init__(
        self,
        coordinator: QuinLEDReleaseCoordinator,
        device_entry: dr.DeviceEntry,
        wled_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_entry.id
        self._host: str | None = wled_entry.data.get(CONF_HOST)
        self._attr_unique_id = f"{DOMAIN}_{device_entry.id}"
        self._attr_device_info = DeviceInfo(identifiers=device_entry.identifiers)

    @property
    def _device(self) -> dr.DeviceEntry | None:
        return dr.async_get(self.hass).async_get(self._device_id)

    @property
    def available(self) -> bool:
        return super().available and self._device is not None

    @property
    def installed_version(self) -> str | None:
        device = self._device
        return device.sw_version if device else None

    @property
    def latest_version(self) -> str | None:
        return self.coordinator.data.version

    @property
    def release_url(self) -> str:
        return GITHUB_RELEASES_URL

    async def async_install(self, version: str | None, backup: bool, **kwargs) -> None:
        """Download the matching QuinLED-Firmware asset and flash the device."""
        device = self._device
        if device is None or not self._host:
            raise HomeAssistantError(
                f"Cannot update {self.entity_id}: device or host is unknown"
            )

        model = device.model or ""
        asset_name = MODEL_ASSET_MAP.get(model, model)
        release_version = self.coordinator.data.version
        filename = f"{ASSET_PREFIX}_{release_version}_{asset_name}.bin"

        if filename not in self.coordinator.data.asset_filenames:
            available = ", ".join(sorted(self.coordinator.data.asset_filenames))
            raise HomeAssistantError(
                f"No matching QuinLED-Firmware release asset for '{device.name}' "
                f"(self-reported model '{model}', tried filename '{filename}'). "
                f"Available assets in release v{release_version}: {available}. "
                "If this board was renamed upstream, add a MODEL_ASSET_MAP entry "
                "in the quinled_updater integration."
            )

        download_url = GITHUB_ASSET_DOWNLOAD_URL.format(
            version=release_version, filename=filename
        )
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(download_url) as response:
                if response.status != 200:
                    raise HomeAssistantError(
                        f"Failed to download firmware for '{device.name}': "
                        f"HTTP {response.status} from {download_url}"
                    )
                firmware_bytes = await response.read()
        except HomeAssistantError:
            raise
        except Exception as err:  # noqa: BLE001 - re-raised as HomeAssistantError
            raise HomeAssistantError(
                f"Error downloading firmware for '{device.name}' from "
                f"{download_url}: {err}"
            ) from err

        form = aiohttp.FormData()
        form.add_field(
            OTA_UPLOAD_FIELD_NAME,
            firmware_bytes,
            filename=filename,
            content_type="application/octet-stream",
        )
        upload_url = f"http://{self._host}{OTA_PATH}"

        try:
            async with session.post(upload_url, data=form) as response:
                if response.status != 200:
                    body = await response.text()
                    raise HomeAssistantError(
                        f"Firmware upload to '{device.name}' ({upload_url}) failed: "
                        f"HTTP {response.status}: {body[:200]}"
                    )
        except HomeAssistantError:
            raise
        except Exception as err:  # noqa: BLE001 - re-raised as HomeAssistantError
            raise HomeAssistantError(
                f"Error uploading firmware to '{device.name}' at {upload_url}: {err}"
            ) from err

        _LOGGER.info(
            "Flashed %s to '%s' (%s)", filename, device.name, self._host
        )
        await self.coordinator.async_request_refresh()
