"""Support for the SamsungTV remote."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
import logging
from typing import Any

from homeassistant.components.media_player.const import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    DOMAIN as MP_DOMAIN,
    SERVICE_PLAY_MEDIA,
)
from homeassistant.components.remote import ATTR_NUM_REPEATS, RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_SERVICE,
    CONF_SERVICE_DATA,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.service import CONF_SERVICE_ENTITY_ID, async_call_from_config

from . import SamsungTVDeviceInfo
from .const import DATA_DEV_INFO, DOMAIN
from .media_player import MEDIA_TYPE_KEY

JOIN_COMMAND = "+"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Samsung TV from a config entry."""

    @callback
    def _add_remote_entity(utc_now: datetime) -> None:
        """Create remote entity."""
        mp_entity_id = None
        entity_reg = er.async_get(hass)
        tv_entries = er.async_entries_for_config_entry(entity_reg, entry.entry_id)
        for tv_entity in tv_entries:
            if tv_entity.domain == MP_DOMAIN:
                mp_entity_id = tv_entity.entity_id
                break

        if mp_entity_id is None:
            return

        dev_info: SamsungTVDeviceInfo = hass.data[DOMAIN][entry.entry_id][DATA_DEV_INFO]
        async_add_entities([SamsungTVRemote(mp_entity_id, dev_info)])

    # we wait for TV media player entity to be created
    async_call_later(hass, 5, _add_remote_entity)


class SamsungTVRemote(RemoteEntity):
    """Device that sends commands to a SamsungTV."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False

    def __init__(self, mp_entity_id: str, dev_info: SamsungTVDeviceInfo):
        """Initialize the remote."""
        self._mp_entity_id = mp_entity_id
        self._attr_unique_id = dev_info.unique_id
        self._attr_device_info = dev_info.device_info

    async def _async_call_service(
        self,
        service_name,
        variable_data=None,
    ):
        """Call a HA service."""
        service_data = {
            CONF_SERVICE: f"{MP_DOMAIN}.{service_name}",
            CONF_SERVICE_ENTITY_ID: self._mp_entity_id,
        }

        if variable_data:
            service_data[CONF_SERVICE_DATA] = variable_data

        try:
            await async_call_from_config(
                self.hass,
                service_data,
                blocking=True,
                validate_config=True,
            )
        except HomeAssistantError as ex:
            _LOGGER.error("SamsungTV Smart Remote - error %s", ex)

        return

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""

        await self._async_call_service(SERVICE_TURN_OFF)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""

        await self._async_call_service(SERVICE_TURN_ON)

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send a command to a device.

        Supported keys vary between models.
        See https://github.com/jaruba/ha-samsungtv-tizen/blob/master/Key_codes.md
        """
        num_repeats = kwargs[ATTR_NUM_REPEATS]
        commands = JOIN_COMMAND.join(command)
        content_id = commands
        for _ in range(num_repeats - 1):
            content_id += f"{JOIN_COMMAND}{commands}"

        service_data = {
            ATTR_MEDIA_CONTENT_TYPE: MEDIA_TYPE_KEY,
            ATTR_MEDIA_CONTENT_ID: content_id,
        }
        await self._async_call_service(SERVICE_PLAY_MEDIA, service_data)
