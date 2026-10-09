"""Tests for the Alpicool switch entities."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.alpicool_ble.const import DOMAIN, BatteryProtection
from custom_components.alpicool_ble.switch import (
    AlpicoolBatterySaverSwitch,
    async_setup_entry,
)

ADDRESS = "AA:BB:CC:DD:EE:FF"


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN, data={"address": ADDRESS, "name": "Fridge"}, options={}
    )


def _api(**status) -> MagicMock:
    api = MagicMock()
    api.status = status
    api.is_available = True
    api.async_set_values = AsyncMock()
    api.update_status = AsyncMock(return_value=True)
    return api


def make_switch(level: BatteryProtection, **status) -> AlpicoolBatterySaverSwitch:
    """Return a battery saver switch wired to a fake API."""
    return AlpicoolBatterySaverSwitch(_entry(), _api(**status), level)


async def test_setup_adds_the_lock_and_one_switch_per_level() -> None:
    """The lock keeps its place and every battery saver level gets a switch."""
    added: list = []
    hass = MagicMock()
    entry = _entry()
    hass.data = {DOMAIN: {entry.entry_id: _api(bat_saver=2)}}

    await async_setup_entry(hass, entry, added.extend)

    assert [e.unique_id for e in added] == [
        f"{ADDRESS}_lock",
        f"{ADDRESS}_battery_saver_low",
        f"{ADDRESS}_battery_saver_medium",
        f"{ADDRESS}_battery_saver_high",
    ]
    assert [e.name for e in added[1:]] == [
        "Battery Saver Low",
        "Battery Saver Medium",
        "Battery Saver High",
    ]


@pytest.mark.parametrize("active", list(BatteryProtection))
def test_exactly_the_active_level_is_on(active: BatteryProtection) -> None:
    """Only the switch of the level the fridge reports is on."""
    states = {
        level: make_switch(level, bat_saver=int(active)).is_on
        for level in BatteryProtection
    }

    assert states == {level: level is active for level in BatteryProtection}


def test_state_is_unknown_without_a_reading() -> None:
    """No status yet, or a fridge that is away, is not the same as off."""
    assert make_switch(BatteryProtection.HIGH).is_on is None

    switch = make_switch(BatteryProtection.HIGH, bat_saver=2)
    switch.api.is_available = False
    assert switch.is_on is None


async def test_turning_on_selects_the_level() -> None:
    """Switching a level on sends that level to the fridge."""
    switch = make_switch(BatteryProtection.MEDIUM, bat_saver=2)
    switch.hass = MagicMock()

    await switch.async_turn_on()

    switch.api.async_set_values.assert_awaited_once_with({"bat_saver": 1})
    switch.api.update_status.assert_awaited_once()


async def test_turning_off_sends_nothing() -> None:
    """The fridge always has a level, so switching the active one off keeps it."""
    switch = make_switch(BatteryProtection.HIGH, bat_saver=2)
    switch.async_write_ha_state = MagicMock()

    await switch.async_turn_off()

    switch.api.async_set_values.assert_not_awaited()
    switch.async_write_ha_state.assert_called_once()
    assert switch.is_on is True
