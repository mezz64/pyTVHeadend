"""Support for TVHeadEnd sensors."""
import logging

from homeassistant.const import (EVENT_STATE_CHANGED, ATTR_ENTITY_ID)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
import homeassistant.components.input_select as input_select
from . import (
    CONF_SENSORS, DATA_TVH, SIGNAL_UPDATE_TVH)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the eight sleep sensors."""
    if discovery_info is None:
        return

    name = 'tvheadend'
    sensors = discovery_info[CONF_SENSORS]
    tvh = hass.data[DATA_TVH]

    all_sensors = []

    for index, sensor in enumerate(sensors):
        sname = '{}_{}'.format(name, index)
        all_sensors.append(TVHSensor(hass, sname, tvh.stream_list[index]))

    async_add_entities(all_sensors, True)


class TVHSensor(Entity):
    """TVH sensor representation."""

    def __init__(self, hass, name, stream):
        """Initialize of a TVH sensor."""
        self.hass = hass
        self._stream = stream
        self._name = name
        self._state = self._stream.channel_name
        # self._update_input_select()
        _LOGGER.debug('Setup new stream sensor: {}'.format(name))

        self._input_entity = 'input_select.tv_stream_{}'.format(self._name.split('_')[1])
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._handle_input_select_updates)

    async def _handle_input_select_updates(self, event):
        """Handle state change updates for input_select"""
        entity_id = event.data.get(ATTR_ENTITY_ID)
        if entity_id != self._input_entity:
            return

        new_state = event.data.get('new_state').state
        # _LOGGER.debug('Params - entity: %s, new_state: %s, active_stream: %s', entity_id, new_state, self._stream.active_service)
        if new_state == "Inactive":
            return

        if new_state != self._stream.active_service:
            # We must want to change the service
            _LOGGER.debug('Action user-input on: {} to state {}'.format(entity_id, new_state))
            await self._stream.change_service(new_state)

    async def async_added_to_hass(self):
        """Register update dispatcher."""

        @callback
        def async_tvh_update():
            """Update callback."""
            # _LOGGER.debug('Running sensor update callback.')
            self.async_schedule_update_ha_state(True)

        async_dispatcher_connect(
            self.hass, SIGNAL_UPDATE_TVH, async_tvh_update)

    @property
    def name(self):
        """Return the channel name of the stream."""
        index = self._name.split('_')[1]
        return 'TV Stream #{}'.format(index)

    @property
    def available(self):
        """Return True if entity is available."""
        return self._stream.is_active

    @property
    def icon(self):
        """Return the icon"""
        return 'mdi:television-classic'

    @property
    def should_poll(self):
        """No polling needed within TVH."""
        return False

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    async def async_update(self):
        """Update latest state"""
        self._state = self._stream.channel_name
        await self._update_input_select(self._stream.active_service)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        state_attr = {'active_service': self._stream.active_service}
        state_attr['service_list'] = self._stream.service_name_list
        return state_attr

    async def _update_input_select(self, option=None):
        """Update associated input select"""

        if self.hass.states.get(self._input_entity) is None:
            _LOGGER.error("%s is not a valid input_select entity.", self._input_entity)
            return
        else:
            curr_state = self.hass.states.get(self._input_entity).state
            # _LOGGER.debug('{}, state: {}'.format(input_entity, curr_state))

        if not self._stream.service_name_list:
            if curr_state == 'Inactive':
                return
            data = {"options": ["Inactive"], "entity_id": self._input_entity}
        else:
            if curr_state == option:
                return
            data = {"options": self._reorder_list(
                self._stream.service_name_list, option),
                    "entity_id": self._input_entity}

        _LOGGER.debug('Update input_select with: {}'.format(data))
        await self.hass.services.async_call(
            input_select.DOMAIN, input_select.SERVICE_SET_OPTIONS, data)

        if option:
            data = {"option": option, "entity_id": self._input_entity}
            if curr_state != option:
                await self.hass.services.async_call(
                    input_select.DOMAIN, input_select.SERVICE_SELECT_OPTION, data)

    def _reorder_list(self, inlist, first=None):
        """Reorder given list moving specified value to index 0."""
        new_list = [None] * (len(inlist))
        if first in inlist:
            new_list[0] = first
        else:
            _LOGGER.error("Desired first item isn't in list, returning original list.")
            return inlist

        new_i = 1
        for item in inlist:
            if item != first:
                new_list[new_i] = item
                new_i += 1

        if len(new_list) == len(inlist):
            return new_list
        else:
            _LOGGER.error("New list is longer than input, aborting.")
            return inlist
