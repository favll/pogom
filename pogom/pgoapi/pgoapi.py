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
from Queue import Queue, PriorityQueue

from . import __title__, __version__, __copyright__
from .rpc_api import RpcApi
from .auth_ptc import AuthPtc
from .auth_google import AuthGoogle
from .exceptions import AuthException, NotLoggedInException, ServerBusyOrOfflineException, NoPlayerPositionSetException, EmptySubrequestChainException, ServerApiEndpointRedirectException, AuthTokenExpiredException

from . import protos
from POGOProtos.Networking.Requests.RequestType_pb2 import RequestType

logger = logging.getLogger(__name__)


class PGoApi:
    def __init__(self, signature_lib_path):
        self.set_logger()

        self._signature_lib_path = signature_lib_path
        self._work_queue = Queue()
        self._auth_queue = PriorityQueue()
        self._workers = []
        self._api_endpoint = 'https://pgorelease.nianticlabs.com/plfe/rpc'

        self.log.info('%s v%s - %s', __title__, __version__, __copyright__)

    def create_workers(self, num_workers):
        for i in xrange(num_workers):
            worker = PGoApiWorker(self._signature_lib_path, self._work_queue, self._auth_queue)
            worker.daemon = True
            worker.start()
            self._workers.append(worker)

    def resize_workers(self, num_workers):
        workers_now = len(self._workers)
        if workers_now < num_workers:
            self.create_workers(num_workers - workers_now)
        elif workers_now > num_workers:
            for i in xrange(workers_now - num_workers):
                worker = self._workers.pop()
                worker.stop()

    def set_accounts(self, accounts):
        old_accounts = []
        new_accounts = []

        accounts_todo = {}
        for account in accounts:
            accounts_todo[account['username']] = accounts['password']

        while not self._auth_queue.empty():
            # Go through accounts in auth queue and only add those back
            # that we still want to use
            next_call, auth_provider = self._auth_queue.get()
            if auth_provider.username in accounts_todo:
                old_accounts.append((next_call, auth_provider))
                del accounts_todo[auth_provider.username]

        while old_accounts:
            self._auth_queue.put(old_accounts.pop())

        # Add new accounts
        for username, password in accounts_todo.iteritems():
            new_accounts.append({'username': username, 'password': password})
        add_accounts(new_accounts)

    def add_accounts(self, accounts):
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

            self._auth_queue.put((time.time(), auth_provider))

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
                self.log.debug(
                   "Adding '%s' to RPC request including arguments", name)
                self.log.debug("Arguments of '%s': \n\r%s", name, kwargs)
            else:
                method = RequestType.Value(name)
                self.log.debug("Adding '%s' to RPC request", name)

            self.call_method(method, position, callback)

        if func.upper() in RequestType.keys():
            return function
        else:
            raise AttributeError

    def call_method(self, method, position, callback):
        self._work_queue.put((method, position, callback))

    def empty_work_queue(self):
        while not self._work_queue.empty():
            try:
                self._work_queue.get(False)
                self._work_queue.task_done()
            except Queue.Empty:
                return

    def is_work_queue_empty(self):
        return self._work_queue.empty()

    def wait_until_done(self):
        self._work_queue.join()


class PGoApiWorker(Thread):
    THROTTLE_TIME = 10.0
    # In case the server returns a status code 3, this has to be requested
    SC_3_REQUESTS = [RequestType.Value("GET_PLAYER")]

    def __init__(self, signature_lib_path, work_queue, auth_queue):
        Thread.__init__(self)
        self.log = logging.getLogger(__name__)
        self._running = True

        self._work_queue = work_queue
        self._auth_queue = auth_queue

        self._session = requests.session()
        self._session.headers.update({'User-Agent': 'Niantic App'})
        self._session.verify = True

        self.rpc_api = RpcApi(None)
        self.rpc_api._session = self._session
        self.rpc_api.activate_signature(signature_lib_path)

    def _get_auth_provider(self):
        while True:  # Maybe change this loop to something more beautiful?
            next_call, auth_provider = self._auth_queue.get()
            if (time.time() + self.THROTTLE_TIME < next_call):
                # Probably one of the sidelined auth providers, skip it
                self._auth_queue.put((next_call, auth_provider))
            else:
                # Sleep until the auth provider is ready
                if (time.time() < next_call):  # Kind of a side effect -> bad
                    time.sleep(max(next_call - time.time(), 0))
                return (next_call, auth_provider)

    def run(self):
        while self._running:
            method, position, callback = self._work_queue.get()
            if not self._running:
                self._work_queue.put((method, position, callback))
                self._work_queue.task_done()
                continue

            next_call, auth_provider = self._get_auth_provider()
            if not self._running:
                self._auth_queue.put((next_call, auth_provider))
                self._work_queue.put((method, position, callback))
                self._work_queue.task_done()
                continue

            # Let's do this.
            self.rpc_api._auth_provider = auth_provider
            try:
                response = self.call(auth_provider, [method], position)
                next_call = time.time() + self.THROTTLE_TIME
            except Exception as e:
                # Too many login retries lead to an AuthException
                # So let us sideline this auth provider for 5 minutes
                if isinstance(e, AuthException):
                    self.log.error("AuthException in worker thread. Username: {}".format(auth_provider.username))
                    next_call = time.time() + 5 * 60
                else:
                    self.log.error("Error in worker thread. Returning empty response. Error: {}".format(e))
                    next_call = time.time() + self.THROTTLE_TIME

                self._work_queue.put((method, position, callback))
                response = {}

            self._work_queue.task_done()
            self.rpc_api._auth_provider = None
            self._auth_queue.put((next_call, auth_provider))
            callback(response)

    def stop(self):
        self._running = False

    def call(self, auth_provider, req_method_list, position):
        if not req_method_list:
            raise EmptySubrequestChainException()

        lat, lng, alt = position
        if (lat is None) or (lng is None) or (alt is None):
            raise NoPlayerPositionSetException()

        self.log.debug('Execution of RPC')
        response = None

        again = True  # Status code 53 or not logged in?
        retries = 5
        while again:
            self._login_if_necessary(auth_provider, position)

            try:
                response = self.rpc_api.request(auth_provider.get_api_endpoint(), req_method_list, position)
                if not response:
                    raise ValueError('Request returned problematic response: {}'.format(response))
            except (NotLoggedInException, AuthTokenExpiredException):
                pass  # Trying again will trigger login in _login_if_necessary
            except ServerApiEndpointRedirectException as e:
                auth_provider.set_api_endpoint('https://{}/rpc'.format(e.get_redirected_endpoint()))
            except Exception as e:  # Never crash the worker
                if isinstance(e, ServerBusyOrOfflineException):
                    self.log.info('Server seems to be busy or offline: {}'.format(e))
                else:
                    self.log.info('Unexpected error during request: {}'.format(e))
                if retries == 0:
                    return {}
                retries -= 1
            else:
                if 'api_url' in response:
                    auth_provider.set_api_endpoint('https://{}/rpc'.format(response['api_url']))

                if 'status_code' in response and response['status_code'] == 3:
                    self.log.info("Status code 3 returned. Performing get_player request.")
                    req_method_list = self.SC_3_REQUESTS + req_method_list
                    auth_provider.code_three_counter += 1
                elif 'responses' in response and not response['responses']:
                    self.log.info("Received empty map_object response. Logging out and retrying.")
                    auth_provider._access_token_expiry = time.time() # This will trigger a login in _login_if_necessary
                    auth_provider.code_three_counter = 0
                else:
                    again = False
                    auth_provider.code_three_counter = 0
                    
                if auth_provider.code_three_counter > 1:
                    self.log.info("Received two consecutive status_code 3 on account {}, probably banned.".format(auth_provider.username))

        return response

    def _login(self, auth_provider, position):
        self.log.info('Attempting login: {}'.format(auth_provider.username))
        consecutive_fails = 0

        while not auth_provider.user_login():
            sleep_t = min(math.exp(consecutive_fails / 1.7), 5 * 60)
            self.log.info('Login failed, retrying in {:.2f} seconds'.format(sleep_t))
            consecutive_fails += 1
            time.sleep(sleep_t)
            if consecutive_fails == 5:
                raise AuthException('Login failed five times.')

        self.log.info('Login successful: {}'.format(auth_provider.username))

    def _login_if_necessary(self, auth_provider, position):
        if not auth_provider.is_login() or auth_provider._access_token_expiry < time.time() + 120:
            if auth_provider.is_login():
                self.log.info("{} access token has or is about to expire".format(auth_provider.username))
            self._login(auth_provider, position)
