"""
pytvheadend.stream
~~~~~~~~~~~~~~~~~~~~
Provides stream data for TVHeadend
Copyright (c) 2019 John Mihalic <https://github.com/mezz64>
Licensed under the MIT license.

"""
import asyncio
import json
import logging

_LOGGER = logging.getLogger(__name__)


class Stream(object):
    """TVHeadend stream object"""
    def __init__(self, server):
        """Initialize stream object."""
        self.server = server
        self._channel_name = None
        self._active_service = None

        self._service_list = []
        self._service_history = []

    @property
    def is_active(self):
        """Return if active or not"""
        return bool(self._channel_name)

    @property
    def channel_name(self):
        """Return channel name"""
        return self._channel_name

    @property
    def active_service(self):
        """Return currently active service"""
        return self._active_service

    @property
    def service_full_list(self):
        """Return list of services"""
        return self._service_list

    @property
    def service_name_list(self):
        """Return list of service names"""
        tmp_list = []
        for service in self._service_list:
            tmp_list.append(service['name'])
        return tmp_list

    def update_data(self, channel=None):
        """ Update subscription object. """
        if not channel:
            self._channel_name = None
            self._active_service = None
            self._service_list = []
            self._service_history = []
            _LOGGER.debug('Stream object cleared.')
        else:
            self._channel_name = channel['name']
            if channel['network'] != self._active_service:
                self._active_service = channel['network']
                self._service_history.append(self._active_service)
                self.get_channel_info()

            _LOGGER.debug('Channel updated: %s', self._channel_name)

    def get_channel_info(self):
        """Return list of services & muxes based on channel name"""
        options = []
        if not self._channel_name:
            return

        if not self.server.chan_json:
            return

        for chan in self.server.chan_json:
            if chan['name'].upper() == self._channel_name:
                for serv in chan['services']:
                    for mux in self.server.serv_json:
                        if mux['uuid'] == serv:
                            if mux['network'].upper() == self._active_service:
                                active = True
                            else:
                                active = False
                            options.append({
                                'name': mux['network'].upper(),
                                'service_uuid': mux['uuid'],
                                'mux_uuid': mux['multiplex_uuid'],
                                'active': active,
                                })
        self._service_list = options

    async def change_service(self, new_service=None):
        """Change active service"""
        disable_list = []
        enable_list = []
        service_valid = False

        if not self._channel_name:
            return

        # If no service is defined:
        # - Disable active and previously active services
        # - Wait 5s for switch, re-enable services
        if new_service:
            _LOGGER.debug('Changing to %s', new_service)
            # Disable all services except new one
            for network in self._service_list:
                if network['name'] == new_service:
                    service_valid = True
                    _LOGGER.debug('Found Service')

            if service_valid:
                for network in self._service_list:
                    if network['name'] != new_service:
                        disable_list.append({
                            "enabled": "false",
                            "uuid": network['service_uuid']
                            })
                        enable_list.append({
                            "enabled": "true",
                            "uuid": network['service_uuid']
                            })
        else:
            # Disable those we've already tried to get a new option
            # unless we've tried them all, if so reset the list
            if len(self._service_history) == len(self._service_list):
                # We've tried them all, reset history
                _LOGGER.debug('History full, being reset.')
                self._service_history = [self._active_service]

            for service in self._service_history:
                # Build json with the service uuids to disable.
                for network in self._service_list:
                    if service == network['name']:
                        disable_list.append({
                            "enabled": "false",
                            "uuid": network['service_uuid']
                            })
                        enable_list.append({
                            "enabled": "true",
                            "uuid": network['service_uuid']
                            })
        _LOGGER.debug(json.dumps(disable_list))

        # http://192.168.11.5:9981/api/idnode/save
        data = {'node': json.dumps(disable_list)}
        req = await self.server.api_post(
            self.server.root_url + "/api/idnode/save", params=None, data=data)
        if req is None:
            _LOGGER.error('Unable to disable services.')
        else:
            # Wait for service to switch
            await asyncio.sleep(2)
            # Renable all options
            data = {'node': json.dumps(enable_list)}
            req = await self.server.api_post(
                self.server.root_url + "/api/idnode/save", params=None, data=data)

        # Force update after we make a change
        await self.server.fetch_subscription_list(force=True)
