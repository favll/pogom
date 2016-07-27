#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import math
import time
from sys import maxint
import collections
import cProfile
from geographiclib.geodesic import Geodesic

from pgoapi import PGoApi
from pgoapi.utilities import f2i, get_cellid, get_pos_by_name
from .models import parse_map, SearchConfig

log = logging.getLogger(__name__)

TIMESTAMP = '\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000'
api = PGoApi()
queue = collections.deque()
consecutive_map_fails = 0

scan_start_time = 0
min_time_per_scan = 3 * 60


def set_cover():
    lat = SearchConfig.ORIGINAL_LATITUDE
    lng = SearchConfig.ORIGINAL_LONGITUDE

    d = math.sqrt(3) * 100
    points = [[{'lat2': lat, 'lon2': lng, 's': 0}]]

    for i in xrange(1, maxint):
        oor_counter = 0

        points.append([])
        for j in range(0, 6 * i):
            p = points[i - 1][(j - j / i - 1 + (j % i == 0))]
            p_new = Geodesic.WGS84.Direct(p['lat2'], p['lon2'], (j+i-1)/i * 60, d)
            p_new['s'] = Geodesic.WGS84.Inverse(p_new['lat2'], p_new['lon2'], lat, lng)['s12']
            points[i].append(p_new)

            if p_new['s'] > SearchConfig.RADIUS:
                oor_counter += 1

        if oor_counter == 6 * i:
            break

    cover = [{"lat": p['lat2'], "lng": p['lon2']}
             for sublist in points for p in sublist if p['s'] < SearchConfig.RADIUS]
    SearchConfig.COVER = cover


def set_location(location, radius):
    position = get_pos_by_name(location)
    log.info('Parsed location is: {:.4f}/{:.4f}/{:.4f} (lat/lng/alt)'.
             format(*position))

    SearchConfig.ORIGINAL_LATITUDE = position[0]
    SearchConfig.ORIGINAL_LONGITUDE = position[1]
    SearchConfig.RADIUS = radius


def send_map_request(api, position, args):
    try:
        login_if_necessary(args, position)

        api.set_position(*position)
        api.get_map_objects(latitude=f2i(position[0]),
                            longitude=f2i(position[1]),
                            since_timestamp_ms=TIMESTAMP,
                            cell_id=get_cellid(position[0], position[1]))
        return api.call()
    except Exception:  # make sure we dont crash in the main loop
        log.exception("Uncaught exception when downloading map")
        return False


def generate_location_steps():
    for point in SearchConfig.COVER:
        yield (point["lat"], point["lng"], 0)


def login(args, position):
    SearchConfig.LOGGED_IN = 0
    log.info('Attempting login')
    consecutive_fails = 0

    api.set_position(*position)

    while not api.login(args.auth_service, args.username, args.password):
        sleep_t = min(math.exp(consecutive_fails / 1.7), 5 * 60)
        log.info('Login failed, retrying in {:.2f} seconds'.format(sleep_t))
        consecutive_fails += 1
        time.sleep(sleep_t)

    SearchConfig.LOGGED_IN = time.time()
    log.info('Login successful')


def login_if_necessary(args, position):
    global api
    if api._rpc.auth_provider and api._rpc.auth_provider._ticket_expire:
        remaining_time = api._rpc.auth_provider._ticket_expire / 1000 - time.time()

        if remaining_time < 60:
            log.info("Login has or is about to expire")
            login(args, position)
    else:
        login(args, position)


def search(args, req_sleep=1):
    num_steps = len(SearchConfig.COVER)

    i = 1
    for step_location in generate_location_steps():
        log.debug('Scanning step {:d} of {:d}.'.format(i, num_steps))
        log.debug('Scan location is {:f}, {:f}'.format(step_location[0], step_location[1]))

        response_dict = send_map_request(api, step_location, args)
        while not response_dict:
            log.info('Map Download failed. Trying again.')
            response_dict = send_map_request(api, step_location, args)
            time.sleep(req_sleep)

        try:
            parse_map(response_dict)
        except KeyError:
            log.exception('Failed to parse response: {}'.format(response_dict))
        except:  # make sure we dont crash in the main loop
            log.exception('Unexpected error')

        SearchConfig.LAST_SUCCESSFUL_REQUEST = time.time()
        log.info('Completed {:5.2f}% of scan.'.format(float(i) / num_steps * 100))

        if SearchConfig.CHANGE:
            SearchConfig.CHANGE = False
            break

        i += 1


def search_async(args):
    num_steps = len(SearchConfig.COVER)

    log.info("Starting scan of {} locations".format(num_steps))

    i = 1
    while len(queue) > 0:
        c = queue.pop()
        step_location = (c["lat"], c["lng"], 0)
        log.debug('Scanning step {:d} of {:d}.'.format(i, num_steps))
        log.debug('Scan location is {:f}, {:f}'.format(step_location[0], step_location[1]))

        login_if_necessary(args, step_location)
        error_throttle()

        api.set_position(*step_location)
        api.get_map_objects(latitude=f2i(step_location[0]),
                            longitude=f2i(step_location[1]),
                            since_timestamp_ms=TIMESTAMP,
                            cell_id=get_cellid(step_location[0], step_location[1]))
        api.call_async(callback)

        if SearchConfig.CHANGE:
            log.info("Changing scan location")
            SearchConfig.CHANGE = False
            queue.clear()
            queue.extend(SearchConfig.COVER)

        if (i % 20 == 0):
            log.info(api._rpc._curl.stats())

        i += 1

    api.finish_async()
    log.info(api._rpc._curl.stats())
    api._rpc._curl.reset_stats()


def error_throttle():
    if consecutive_map_fails == 0:
        return

    sleep_t = min(math.exp(1.0 * consecutive_map_fails / 5) - 1, 2*60)
    log.info('Loading map failed, waiting {:.5f} seconds'.format(sleep_t))

    start_sleep = time.time()
    api.finish_async(sleep_t)
    time.sleep(max(start_sleep + sleep_t - time.time(), 0))


def callback(response_dict):
    global consecutive_map_fails
    if (not response_dict) or ('responses' in response_dict and not response_dict['responses']):
        log.info('Map Download failed. Trying again.')
        consecutive_map_fails += 1
        return

    try:
        parse_map(response_dict)
        SearchConfig.LAST_SUCCESSFUL_REQUEST = time.time()
        consecutive_map_fails = 0
        log.debug("Parsed & saved.")
    except KeyError:
        log.exception('Failed to parse response: {}'.format(response_dict))
        consecutive_map_fails += 1
    except:  # make sure we dont crash in the main loop
        log.exception('Unexpected error while parsing response: {}'.format(response_dict))
        consecutive_map_fails += 1


def throttle():
    if scan_start_time == 0:
        return

    sleep_time = max(min_time_per_scan - (time.time() - scan_start_time), 0)
    log.info("Scan finished. Sleeping {:.2f} seconds before continuing.".format(sleep_time))
    SearchConfig.LAST_SUCCESSFUL_REQUEST = -1
    time.sleep(sleep_time)


def search_loop_async(args):
    global scan_start_time
    while True:
        throttle()

        scan_start_time = time.time()
        queue.extend(SearchConfig.COVER[::-1])
        search_async(args)
        SearchConfig.COMPLETE_SCAN_TIME = time.time() - scan_start_time


def search_loop(args):
    global scan_start_time
    while True:
        scan_start_time = time.time()
        search(args)
        log.info("Finished scan")
        SearchConfig.COMPLETE_SCAN_TIME = time.time() - scan_start_time
