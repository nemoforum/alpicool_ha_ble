"""Switch platform for the Alpicool BLE integration."""

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import FridgeApi
from .const import DOMAIN, BatteryProtection
from .entity import AlpicoolEntity

BATTERY_SAVER_ICONS = {
    BatteryProtection.LOW: "mdi:battery-low",
    BatteryProtection.MEDIUM: "mdi:battery-medium",
    BatteryProtection.HIGH: "mdi:battery-high",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Alpicool switch entities."""
    api: FridgeApi = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AlpicoolLockSwitch(entry, api),
            *(
                AlpicoolBatterySaverSwitch(entry, api, level)
                for level in BatteryProtection
            ),
        ]
    )


class AlpicoolLockSwitch(AlpicoolEntity, SwitchEntity):
    """Representation of the Alpicool lock switch."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: ConfigEntry, api: FridgeApi) -> None:
        """Initialize the switch."""
        super().__init__(entry, api)
        self._attr_unique_id = f"{self._address}_lock"
        self._attr_name = "Lock"

    @property
    def is_on(self) -> bool | None:
        """Return true if the lock is on."""
        if not self.available:
            return None
        return self.api.status.get("locked", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the lock on."""
        await self.api.async_set_values({"locked": True})
        await self._async_refresh_after_write()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the lock off."""
        await self.api.async_set_values({"locked": False})
        await self._async_refresh_after_write()


class AlpicoolBatterySaverSwitch(AlpicoolEntity, SwitchEntity):
    """One of three switches that pick the battery saver level.

    They mirror the Battery Saver select as buttons: exactly one of Low,
    Medium and High is on, and switching one on switches the others off.
    """

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, entry: ConfigEntry, api: FridgeApi, level: BatteryProtection
    ) -> None:
        """Initialize the switch for one battery saver level."""
        super().__init__(entry, api)
        self._level = level
        self._attr_unique_id = f"{self._address}_battery_saver_{level.name.lower()}"
        self._attr_name = f"Battery Saver {level.name.capitalize()}"
        self._attr_icon = BATTERY_SAVER_ICONS[level]

    @property
    def is_on(self) -> bool | None:
        """Return true if the fridge is set to this level."""
        if not self.available:
            return None
        bat_saver = self.api.status.get("bat_saver")
        if bat_saver is None:
            return None
        return bat_saver == self._level

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Select this level; the other two switches follow on the refresh."""
        await self.api.async_set_values({"bat_saver": int(self._level)})
        await self._async_refresh_after_write()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Keep the level: the fridge always has one, so there is no "off".

        Nothing is sent. Writing the state again makes the UI show the switch
        as on, which is still true. Pick another level to change it.
        """
        self.async_write_ha_state()
