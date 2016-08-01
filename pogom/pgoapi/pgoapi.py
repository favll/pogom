"""
pgoapi - Pokemon Go API
Copyright (c) 2016 tjado <https://github.com/tejado>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
OR OTHER DEALINGS IN THE SOFTWARE.

Author: tjado <https://github.com/tejado>
"""

# from __future__ import absolute_import

import re
import six
import logging
import requests
import time
import math
from threading import Thread
from Queue import Queue

from . import __title__, __version__, __copyright__
from .rpc_api import RpcApi
from .auth_ptc import AuthPtc
from .auth_google import AuthGoogle
from .exceptions import AuthException, NotLoggedInException, ServerBusyOrOfflineException, NoPlayerPositionSetException, EmptySubrequestChainException

from . import protos
from POGOProtos.Networking.Requests_pb2 import RequestType

logger = logging.getLogger(__name__)


class PGoApi:
    def __init__(self):
        self.set_logger()

        self._queue = Queue()
        self._workers = []
        self._api_endpoint = 'https://pgorelease.nianticlabs.com/plfe/rpc'

        self.log.info('%s v%s - %s', __title__, __version__, __copyright__)

    def add_workers(self, accounts):
        for account in accounts:
            username, password = account['username'], account['password']
            if not isinstance(username, six.string_types) or not isinstance(password, six.string_types):
                raise AuthException("Username/password not correctly specified")

            provider = account.get('provider', 'ptc')
            if provider == 'ptc':
                auth_provider = AuthPtc(username, password)
            elif provider == 'google':
                auth_provider = AuthGoogle(username, password)
            else:
                raise AuthException("Invalid authentication provider - only ptc/google available.")

            worker = PGoApiWorker(self._queue, self._api_endpoint, auth_provider)
            worker.daemon = True
            worker.start()
            self._workers.append(worker)

        return True

    def set_logger(self, logger=None):
        self.log = logger or logging.getLogger(__name__)

    def get_api_endpoint(self):
        return self._api_endpoint

    def __getattr__(self, func):
        def function(**kwargs):
            name = func.upper()

            position = kwargs.pop('position')
            callback = kwargs.pop('callback')

            if kwargs:
                method = {RequestType.Value(name): kwargs}
                self.log.info(
                   "Adding '%s' to RPC request including arguments", name)
                self.log.debug("Arguments of '%s': \n\r%s", name, kwargs)
            else:
                method = RequestType.Value(name)
                self.log.info("Adding '%s' to RPC request", name)

            self.call_method(method, position, callback)

        if func.upper() in RequestType.keys():
            return function
        else:
            raise AttributeError

    def call_method(self, method, position, callback):
        self._queue.put((method, position, callback))

    def empty_queue(self):
        while not self._queue.empty():
            try:
                self._queue.get(False)
                self.task_done()
            except Queue.Empty:
                return

    def wait_until_done(self):
        self._queue.join()


class PGoApiWorker(Thread):
    def __init__(self, queue, api_endpoint, auth_provider):
        Thread.__init__(self)
        self.log = logging.getLogger(__name__)

        self._queue = queue
        self.rpc_api = RpcApi(auth_provider)
        """ Inherit necessary parameters """
        self._api_endpoint = api_endpoint
        self._auth_provider = auth_provider

        self._ready_at = time.time()
        self._req_method_list = []

    def run(self):
        while True:
            if (time.time() < self._ready_at):
                time.sleep(self._ready_at - time.time())
            method, position, callback = self._queue.get()
            self._req_method_list.append(method)
            response = self.call(position)
            self._ready_at = time.time() + 5.2
            callback(response)
            self._queue.task_done()

    def call(self, position):
        if not self._req_method_list:
            raise EmptySubrequestChainException()

        lat, lng, alt = position
        if (lat is None) or (lng is None) or (alt is None):
            raise NoPlayerPositionSetException()

        # if self._auth_provider is None or not self._auth_provider.is_login():
        #     self.log.info('Not logged in')
        #     return NotLoggedInException()

        # request = RpcApi(self._auth_provider)

        self._login_if_necessary(position)

        self.log.info('Execution of RPC')
        response = None

        again = True  # Status code 53 or not logged in?
        while again:
            try:
                response = self.rpc_api.request(self._api_endpoint, self._req_method_list, position)
            except ServerBusyOrOfflineException as e:
                self.log.info('Server seems to be busy or offline - try again!')
            except NotLoggedInException:
                self._login_if_necessary(position)
                continue

            if 'api_url' in response:
                self._api_endpoint = 'https://{}/rpc'.format(response['api_url'])

            # Status code 53 indicates an endpoint-response.
            # An endpoint-response returns a valid api url that can be used
            # for the next request, however, it also indicates that there is
            # no usable response data in the current response
            if not ('status_code' in response and response['status_code'] == 53):
                # If current response is not an endpoint-response exit the loop
                again = False

        # cleanup after call execution
        self.log.info('Cleanup of request!')
        self._req_method_list = []

        return response

    def _login(self, position):
        self.log.info('Attempting login')
        consecutive_fails = 0

        while not self._auth_provider.login():
            sleep_t = min(math.exp(consecutive_fails / 1.7), 5 * 60)
            log.info('Login failed, retrying in {:.2f} seconds'.format(sleep_t))
            consecutive_fails += 1
            time.sleep(sleep_t)

        self.log.info('Login successful')

        # log.info('Retrieving auth ticket and api endpoint')
        # pr = RpcEnum.RequestMethod.Value("GET_PLAYER")
        # self.request([pr], player_position, auth_provider=auth_provider)
        # log.info('Retrieved auth ticket and api endpoint')

    def _login_if_necessary(self, position):
        if self._auth_provider._ticket_expire:
            remaining_time = self._auth_provider._ticket_expire / 1000 - time.time()

            if remaining_time < 60:
                self.log.info("Login for {} has or is about to expire".format(self._auth_provider.username))
                self._login(position)
        else:
            self._login(position)
