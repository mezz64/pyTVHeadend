"""Support for TVHeadend."""
import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.const import (
    CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD,
    CONF_SENSORS, CONF_SWITCHES, EVENT_HOMEASSISTANT_STOP)
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import (
    async_dispatcher_send)
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util.dt import utcnow

_LOGGER = logging.getLogger(__name__)

CONF_MAXCONN = 'maxconn'

DATA_TVH = 'tvheadend'
DEFAULT_PARTNER = False
DOMAIN = 'tvheadend'

HEAT_ENTITY = 'heat'
USER_ENTITY = 'user'

TVH_SCAN_INTERVAL = timedelta(seconds=30)

SIGNAL_UPDATE_TVH = 'tvh_update'

SERVICE_SERVICE_SET = 'service_set'
SERVICE_SERVICE_SWITCH = 'service_switch'

ATTR_TARGET_INDEX = 'index'
ATTR_TARGET_SERVICE = 'target'

VALID_TARGET_SERVICE = vol.All(vol.Coerce(int), vol.Clamp(min=0, max=100))

SERVICE_TVH_SCHEMA = vol.Schema({
    ATTR_TARGET_INDEX: cv.string,
    ATTR_TARGET_SERVICE: cv.string,
    })

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.port,
        vol.Required(CONF_MAXCONN): cv.string,
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    """Set up the TVHeadend component."""
    from pytvheadend.tvheadend import TVHeadend

    conf = config.get(DOMAIN)
    host = conf.get(CONF_HOST)
    port = conf.get(CONF_PORT)
    user = conf.get(CONF_USERNAME)
    password = conf.get(CONF_PASSWORD)
    maxconn = conf.get(CONF_MAXCONN)

    tvh = TVHeadend(host, port, maxconn=maxconn, loop=hass.loop)

    hass.data[DATA_TVH] = tvh

    # Authenticate, build sensors
    success = await tvh.start()
    if not success:
        # Authentication failed, cannot continue
        return False

    async def async_update_tvh_data(now):
        """Update data from tvh in TVH_SCAN_INTERVAL."""
        await tvh.fetch_subscription_list()
        async_dispatcher_send(hass, SIGNAL_UPDATE_TVH)

        async_track_point_in_utc_time(
            hass, async_update_tvh_data, utcnow() + TVH_SCAN_INTERVAL)

    @callback
    def force_update_tvh_data(msg):
        """Force update of all data"""
        _LOGGER.debug('TVHeadend Force Update Callback fired.')
        async_dispatcher_send(hass, SIGNAL_UPDATE_TVH)

    await async_update_tvh_data(None)
    tvh.add_update_callback(force_update_tvh_data)

    # Load sub components
    sensors = []
    switches = []
    if tvh.stream_list:
        for index, stream in enumerate(tvh.stream_list):
            obj_id = 'tvheadend_stream_{}'.format(index)
            sensors.append(obj_id)
            switches.append(obj_id)
    else:
        # No streams, cannot continue
        return False

    hass.async_create_task(discovery.async_load_platform(
        hass, 'sensor', DOMAIN, {
            CONF_SENSORS: sensors,
        }, config))

    hass.async_create_task(discovery.async_load_platform(
        hass, 'switch', DOMAIN, {
            CONF_SWITCHES: switches,
        }, config))

    async def async_service_handler(service):
        """Handle tvh service calls."""
        params = service.data.copy()

        index = int(params.pop(ATTR_TARGET_INDEX, None))
        target = params.pop(ATTR_TARGET_SERVICE, None)

        await tvh.stream_list[index].change_service(target.upper())

    # Register services
    hass.services.async_register(
        DOMAIN, SERVICE_SERVICE_SWITCH, async_service_handler,
        schema=SERVICE_TVH_SCHEMA)

    async def stop_tvh(event):
        """Handle stopping tvh api session."""
        await tvh.stop()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_tvh)

    return True
