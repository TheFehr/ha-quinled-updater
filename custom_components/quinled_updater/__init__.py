"""The QuinLED Firmware Updater integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .coordinator import QuinLEDReleaseCoordinator

PLATFORMS = ["update"]

type QuinLEDConfigEntry = ConfigEntry[QuinLEDReleaseCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: QuinLEDConfigEntry) -> bool:
    """Set up QuinLED Firmware Updater from a config entry."""
    coordinator = QuinLEDReleaseCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: QuinLEDConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: QuinLEDConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow the user to manually delete a device from the UI/API.

    All of our devices are derived (merged onto an existing wled device, or
    a leftover stray from a prior version's device linkage), so removal is
    always safe: the coordinator re-adds the entity next refresh if the
    underlying wled device is still around, and does nothing if it isn't.
    """
    return True
