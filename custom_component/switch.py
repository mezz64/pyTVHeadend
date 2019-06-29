"""Support for TVHeadEnd switches."""
import logging

from . import (
    CONF_SWITCHES, DATA_TVH, SIGNAL_UPDATE_TVH)

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect)
from homeassistant.components.switch import SwitchDevice

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the tvheadend switches."""
    if discovery_info is None:
        return

    name = 'tvheadend'
    switches = discovery_info[CONF_SWITCHES]
    tvh = hass.data[DATA_TVH]

    all_switches = []

    for index, switch in enumerate(switches):
        sname = '{}_{}'.format(name, index)
        all_switches.append(TVHSwitch(sname, tvh.stream_list[index]))

    async_add_entities(all_switches, True)


class TVHSwitch(SwitchDevice):
    """Reprentation of a TVH switch."""

    def __init__(self, name, stream):
        """Initialize of KNX switch."""
        self._stream = stream
        self._name = name

        _LOGGER.debug('Setup new stream switch: {}'.format(name))

    async def async_added_to_hass(self):
        """Register update dispatcher."""
        @callback
        def async_tvh_update():
            """Update callback."""
            self.async_schedule_update_ha_state(True)

        async_dispatcher_connect(
            self.hass, SIGNAL_UPDATE_TVH, async_tvh_update)

    @property
    def name(self):
        """Return the name."""
        index = self._name.split('_')[1]
        return 'TV Stream #{}'.format(index)

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return None

    @property
    def icon(self):
        """Return the icon"""
        return 'mdi:autorenew'

    @property
    def available(self):
        """Return True if entity is available."""
        return self._stream.is_active

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._stream.change_service()
