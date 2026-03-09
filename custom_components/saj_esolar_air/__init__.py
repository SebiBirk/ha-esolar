"""The eSolar integration."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
import logging
from typing import Any, TypedDict, cast
import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_REGION, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_MONITORED_SITES,
    CONF_PV_GRID_DATA,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
    CONF_PLANT_UPDATE_INTERVAL,
    LEGACY_CONF_UPDATE_INTERVAL_MINUTES,
)
from .esolar import get_esolar_data

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


class ESolarResponse(TypedDict):
    """API response."""
    plantList: list[dict]
    status: str

async def update_listener(hass, entry):
    """Handle options update."""
    _LOGGER.debug("Options updated for %s: %s", entry.entry_id, entry.options)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass, entry):
    """Migrálja a régi konfigurációs bejegyzést az új verzióra."""

    _LOGGER.debug(
        f"Checking migration. Version {entry.version}"
    )

    current_version = entry.version
    legacy_minutes_fallback = LEGACY_CONF_UPDATE_INTERVAL_MINUTES

    if current_version == 1:
        new_fields = {
            CONF_REGION: "eu",
            CONF_PLANT_UPDATE_INTERVAL: 10
        }
        new_data = {**entry.data, **new_fields}  # Új mezők hozzáadása
        hass.config_entries.async_update_entry(entry, data=new_data, version=2)
        legacy_minutes_fallback = new_fields[CONF_PLANT_UPDATE_INTERVAL]
        current_version = 2

    if current_version == 2:
        legacy_interval_minutes = entry.options.get(
            CONF_PLANT_UPDATE_INTERVAL,
            entry.data.get(CONF_PLANT_UPDATE_INTERVAL, legacy_minutes_fallback),
        )
        try:
            update_interval_seconds = max(1, int(legacy_interval_minutes)) * 60
        except (TypeError, ValueError):
            update_interval_seconds = CONF_UPDATE_INTERVAL

        new_options = dict(entry.options)
        new_options[CONF_PLANT_UPDATE_INTERVAL] = update_interval_seconds
        hass.config_entries.async_update_entry(entry, options=new_options, version=3)
    return True


def _get_update_interval_seconds(entry: ConfigEntry) -> int:
    """Return configured polling interval in seconds with a safe fallback."""
    configured = entry.options.get(CONF_PLANT_UPDATE_INTERVAL)
    if configured is None and CONF_PLANT_UPDATE_INTERVAL in entry.data:
        # Legacy versions stored this as minutes in entry.data.
        try:
            return max(1, int(entry.data[CONF_PLANT_UPDATE_INTERVAL])) * 60
        except (TypeError, ValueError):
            return CONF_UPDATE_INTERVAL

    try:
        return max(1, int(configured))
    except (TypeError, ValueError):
        return CONF_UPDATE_INTERVAL

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Beállítja az integrációt a konfigurációs bejegyzés alapján."""
    if not await async_migrate_entry(hass, entry):
        _LOGGER.debug(
            f"Migration failed"
        )
        return False  # Sikertelen migráció esetén ne folytassa
    migrated_entry = hass.config_entries.async_get_entry(entry.entry_id)
    if migrated_entry is not None:
        entry = migrated_entry

    """Set up eSolar from a config entry."""
    coordinator = ESolarCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        domain_data = dict(hass.data[DOMAIN])  # Másolat készítése
        domain_data.pop(entry.entry_id, None)  # Biztonságos törlés
        hass.data[DOMAIN] = domain_data  # Frissített adat visszaírása

    return unload_ok


class ESolarCoordinator(DataUpdateCoordinator[ESolarResponse]):
    """Data update coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        update_interval = timedelta(seconds=_get_update_interval_seconds(entry))
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            always_update=True,
        )
        self._entry = entry

    @property
    def entry_id(self) -> str:
        """Return entry ID."""
        return self._entry.entry_id

    async def _async_update_data(self) -> ESolarResponse:
        """Fetch the latest data from the source."""
        try:
            data = await self.hass.async_add_executor_job(
                get_data, self.hass, self._entry.data, self._entry.options
            )
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed from err
        except ESolarError as err:
            raise UpdateFailed(str(err)) from err
        except Exception as err:  # pylint: disable=broad-except
            raise UpdateFailed(f"Unexpected update error: {err}") from err

        return data

class ESolarError(HomeAssistantError):
    """Base error."""


class InvalidAuth(ESolarError):
    """Raised when invalid authentication credentials are provided."""


class APIRatelimitExceeded(ESolarError):
    """Raised when the API rate limit is exceeded."""


class UnknownError(ESolarError):
    """Raised when an unknown error occurs."""


def get_data(
    hass: HomeAssistant, config: Mapping[str, Any], options: Mapping[str, Any]
) -> ESolarResponse:
    """Get data from the API."""

    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    region = config.get(CONF_REGION)
    plants = options.get(CONF_MONITORED_SITES)
    use_pv_grid_attributes = options.get(CONF_PV_GRID_DATA)

    try:
        _LOGGER.debug(
            "Fetching data with username %s, for plants %s with pv attributes set to %s",
            username,
            plants,
            use_pv_grid_attributes,
        )
        plant_info = get_esolar_data(region, username, password, plants, use_pv_grid_attributes)

    except requests.exceptions.HTTPError as errh:
        _LOGGER.warning("SAJ API HTTP error: %s", errh)
        raise UnknownError(f"SAJ API HTTP error: {errh}") from errh
    except requests.exceptions.ConnectionError as errc:
        _LOGGER.warning("SAJ API connection error: %s", errc)
        raise UnknownError(f"SAJ API connection error: {errc}") from errc
    except requests.exceptions.Timeout as errt:
        _LOGGER.warning("SAJ API timeout: %s", errt)
        raise UnknownError(f"SAJ API timeout: {errt}") from errt
    except requests.exceptions.RequestException as errr:
        _LOGGER.warning("SAJ API request error: %s", errr)
        raise UnknownError(f"SAJ API request error: {errr}") from errr
    except ValueError as err:
        err_str = str(err)

        if "Invalid authentication credentials" in err_str:
            raise InvalidAuth from err
        if "API rate limit exceeded." in err_str:
            raise APIRatelimitExceeded from err

        _LOGGER.exception("Unexpected exception")
        raise UnknownError from err

    else:
        if "error" in plant_info:
            raise UnknownError(plant_info["error"])

        if plant_info.get("status") != "success":
            _LOGGER.exception("Unexpected response: %s", plant_info)
            raise UnknownError
    return cast(ESolarResponse, plant_info)
