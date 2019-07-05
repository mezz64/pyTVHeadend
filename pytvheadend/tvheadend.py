"""
pytvheadend.tvheadend
~~~~~~~~~~~~~~~~~~~~
Provides api for TVHeadend
Copyright (c) 2019 John Mihalic <https://github.com/mezz64>
Licensed under the MIT license.

"""

import logging
import asyncio
import aiohttp
import async_timeout

from pytvheadend.stream import Stream
from pytvheadend.constants import (
    DEFAULT_TIMEOUT, DEFAULT_HEADERS, DEFAULT_PORT,
    SUBSCRIPTIONS_URL, CHANNELS_URL, SERVICES_URL,
    __version__)

_LOGGER = logging.getLogger(__name__)


# Workflow
# Request active subscriptions, keep dictionary of active channel names
# Associate channel name with services by requesting channel grid
# Associate service with mux by requesting service grid
# At this point we have whole chain and can enable/disable services to change the source

# Channel dictionary
# {
#  'id': chann['id'],
# 'name': chann['channel'].upper(),
# 'network': chann['service'].split("/")[1].upper(),
# }

# Easiest way to make this work well with HASS which doesn't
# really support the dynamic add/remove of entities:
# - Define a fixed number of external objects representing total active streams
# - Internally manage stream objects being connected to those objects
# - External objects have a value of either "Inactive" or a given stream

class TVHeadend(object):
    """TVHeadend API object."""
    def __init__(self, host=None, port=DEFAULT_PORT,
                 usr=None, pwd=None, maxconn=1, loop=None):
        """Initialize eight sleep class."""

        _LOGGER.debug("pyTVHeadend %s initializing new server at: %s",
                      __version__, host)

        if not host:
            _LOGGER.error('Host not specified! Cannot continue.')
            return

        self.host = host
        self.usr = usr
        self.pwd = pwd

        self.root_url = 'http://{}:{}'.format(host, port)

        self.chan_json = None
        self.serv_json = None

        self._active_list = []

        self._streams = {}
        self._active_subscriptions = []

        self._ext_list = [None] * int(maxconn)
        for xxx in range(int(maxconn)):
            self._ext_list[xxx] = Stream(self)

        if loop is None:
            _LOGGER.info("Must supply asyncio loop.  Quitting")
            return None
        else:
            self._event_loop = loop
            self._own_loop = False

        asyncio.set_event_loop(self._event_loop)

        self._api_session = aiohttp.ClientSession(
            headers=DEFAULT_HEADERS, loop=self._event_loop)

        # Callbacks
        self._update_callbacks = []

    @property
    def active_subscriptions(self):
        """Return list of current subscriptions."""
        return self._active_subscriptions

    @property
    def active_streams(self):
        """Return dictionary of active streams"""
        return self._streams

    @property
    def stream_list(self):
        """Return external stream list"""
        return self._ext_list

    def add_update_callback(self, callback):
        """Register as callback for when a stream changes."""
        self._update_callbacks.append(callback)
        _LOGGER.debug('Added update callback to %s', callback)

    def remove_update_callback(self, callback):
        """ Remove a registered update callback. """
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)
            _LOGGER.debug('Removed update callback %s',
                          callback)

    def _do_update_callback(self, msg):
        """Call registered callback functions."""
        for callback in self._update_callbacks:
            _LOGGER.debug('Update callback %s by %s',
                          callback, msg)
            self._event_loop.call_soon(callback, msg)

    async def start(self):
        """Start api initialization."""

        await self.fetch_channel_list()
        await self.fetch_service_list()
        return True

    async def stop(self):
        """Stop api session."""
        _LOGGER.debug('Closing tvheadend session.')
        await self._api_session.close()

    async def fetch_subscription_list(self, force=False):
        """Fetch list of active stream subscriptions"""
        # url = '{}/users/me'.format(API_URL)
        streams = []

        slist = await self.api_get(self.root_url + SUBSCRIPTIONS_URL,
                                   {'start': '0', 'limit': '999999999'})
        if slist is None:
            _LOGGER.error('Unable to fetch subscriptions.')
        else:
            # self._devices = dlist['user']['devices']
            # _LOGGER.debug('RAW: %s', slist)
            # _LOGGER.debug('RAW: %s', slist['entries'])
            for chann in slist['entries']:
                try:
                    streams.append({
                        'id': chann['id'],
                        'name': chann['channel'].upper(),
                        'network': chann['service'].split("/")[1].upper(),
                        })
                except KeyError as err:
                    _LOGGER.debug('Error adding stream to list: %s', err)

        self._active_subscriptions = streams
        # _LOGGER.debug(streams)
        self.update_stream_list(streams, force)
        log_str = ""
        for index, obj in enumerate(self._ext_list):
            log_str = log_str + 'Pos: {} - Name: {}, '.format(index, obj.channel_name)

# [{
#   'channel': 'Channel Name',
#   'networks': [{},{},...]
# },...]

# Use dictionary to keep track of channel in external list
#  {ext_list_index: stream_name}
#
#   Loop through active channel list, see if each channel is in the dictionary
#       If not:  Add it - (helper function to get highest empty index)
#       If so: update

    def next_index(self):
        """Return next available index to assign stream"""
        for index, strm in enumerate(self._ext_list):
            if not strm.channel_name:
                # Index is free
                # _LOGGER.debug('Returning available index: %s', index)
                return index

    def update_stream_list(self, streams, force):
        """ Update device list. """
        if streams is None:
            _LOGGER.error('Error updating TVHeadend streams, no data.')
            return

        active_streams = []
        for channel in streams:
            stream_name = '{}.{}'.format(channel['id'], channel['name'])
            active_streams.append(stream_name)

            if stream_name not in self._streams:
                _LOGGER.debug('New stream: %s. Adding to stream list.',
                              stream_name)
                index = self.next_index()
                self._streams[stream_name] = index
                _LOGGER.debug(self._streams)
                # new = Stream(self)
                # self._streams[stream_name] = new
                # new_streams.append(new)

            # Update no matter what
            self._ext_list[self._streams[stream_name]].update_data(channel)
            if force:
                self._do_update_callback(self._streams[stream_name])
            # self._streams[stream_name].update_data(channel)

        # Need to check for no longer active streams and remove
        tmp_strm = self._streams.copy()
        try:
            for stream, index in tmp_strm.items():
                # _LOGGER.debug('1Stream index: %s, Channel: %s', index, stream)
                if stream not in active_streams:
                    # stream no longer active
                    _LOGGER.debug('Old stream: %s. Removing from stream dict.',
                                  stream)
                    # self._streams.pop(stream_id)
                    del self._streams[stream]
                    self._ext_list[index].update_data()
                    # _LOGGER.debug(self._streams)
        except Exception as err:
            # This is a bad idea
            _LOGGER.debug('Caught: %s', err)

    async def fetch_channel_list(self):
        """Fetch channel list"""
        result = await self.api_get(self.root_url + CHANNELS_URL, {'start': '0', 'limit': '999999999'})
        if result is None:
            _LOGGER.error('Unable to fetch channels.')
        else:
            self.chan_json = result['entries']
            # _LOGGER.debug(result)

    async def fetch_service_list(self):
        """Fetch service list"""
        result = await self.api_get(self.root_url + SERVICES_URL, {'start': '0', 'limit': '999999999'})
        if result is None:
            _LOGGER.error('Unable to fetch services.')
        else:
            self.serv_json = result['entries']
            # _LOGGER.debug(result)

    def get_services(self, channel_name):
        """Return list of service IDs based on channel name"""
        if not self.chan_json:
            return

        for chan in self.chan_json:
            if chan['name'] == channel_name:
                return chan['services']

    async def api_post(self, url, params=None, data=None):
        """Make api post request."""
        post = None
        try:
            with async_timeout.timeout(DEFAULT_TIMEOUT, loop=self._event_loop):
                post = await self._api_session.post(
                    url, params=params, data=data)
            if post.status != 200:
                _LOGGER.error('Error posting data: %s', post.status)
                return None

            if 'text/x-json' in post.headers['content-type']:
                post_result = await post.json(content_type='text/x-json')
            else:
                _LOGGER.debug('Response was not JSON, returning text.')
                post_result = await post.text()

            return post_result

        except (aiohttp.ClientError, asyncio.TimeoutError,
                ConnectionRefusedError) as err:
            _LOGGER.error('Error posting data. %s', err)
            return None

    async def api_get(self, url, params=None):
        """Make api fetch request."""
        request = None
        headers = DEFAULT_HEADERS.copy()
        # headers.update({'Session-Token': self._token})

        try:
            with async_timeout.timeout(DEFAULT_TIMEOUT, loop=self._event_loop):
                request = await self._api_session.get(
                    url, headers=headers, params=params)
            # _LOGGER.debug('Get URL: %s', request.url)
            if request.status != 200:
                _LOGGER.error('Error fetching data: %s', request.status)
                return None

            if 'text/x-json' in request.headers['content-type']:
                request_json = await request.json(content_type='text/x-json')
            else:
                _LOGGER.debug('Response was not JSON, returning text.')
                request_json = await request.text()

            return request_json

        except (aiohttp.ClientError, asyncio.TimeoutError,
                ConnectionRefusedError) as err:
            _LOGGER.error('Error fetching data. %s', err)
            return None

    async def api_put(self, url, data=None):
        """Make api put request."""
        put = None
        headers = DEFAULT_HEADERS.copy()
        # headers.update({'Session-Token': self._token})

        try:
            with async_timeout.timeout(DEFAULT_TIMEOUT, loop=self._event_loop):
                put = await self._api_session.put(
                    url, headers=headers, data=data)
            if put.status != 200:
                _LOGGER.error('Error putting data: %s', put.status)
                return None

            if 'text/x-json' in put.headers['content-type']:
                put_result = await put.json(content_type='text/x-json')
            else:
                _LOGGER.debug('Response was not JSON, returning text.')
                put_result = await put.text()

            return put_result

        except (aiohttp.ClientError, asyncio.TimeoutError,
                ConnectionRefusedError) as err:
            _LOGGER.error('Error putting data. %s', err)
            return None
