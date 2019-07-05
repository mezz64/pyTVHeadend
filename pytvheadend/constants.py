"""
pytvheadend.constants
~~~~~~~~~~~~~~~~~~~~
Constants list
Copyright (c) 2019 John Mihalic <https://github.com/mezz64>
Licensed under the MIT license.
"""

MAJOR_VERSION = 0
MINOR_VERSION = 0
SUB_MINOR_VERSION = 2
__version__ = '{}.{}.{}'.format(
    MAJOR_VERSION, MINOR_VERSION, SUB_MINOR_VERSION)

# API_URL = 'https://app-api.8slp.net/v1'

SUBSCRIPTIONS_URL = '/api/status/subscriptions'
CHANNELS_URL = '/api/channel/grid?start=0&limit=999999999'
SERVICES_URL = '/api/mpegts/service/grid?start=0&limit=999999999'
MUXES_URL = '/api/mpegts/mux/grid?start=0&limit=999999999'

DEFAULT_PORT = 9981

DEFAULT_TIMEOUT = 60

DEFAULT_HEADERS = {
    # 'content-type': "application/x-www-form-urlencoded",
    # 'connection': "keep-alive",
    # 'accept': "*/*",
    }
