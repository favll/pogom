#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import math
import time
import collections
import cProfile
import os
import json
from sys import maxint
from geographiclib.geodesic import Geodesic
from datetime import datetime
from itertools import izip, count

from pgoapi import PGoApi
from pgoapi.utilities import f2i, get_cell_ids, get_pos_by_name
from .models import parse_map, SearchConfig
from . import config

log = logging.getLogger(__name__)

consecutive_map_fails = 0
steps_completed = 0
num_steps = 0


def set_cover():
    lat = SearchConfig.ORIGINAL_LATITUDE
    lng = SearchConfig.ORIGINAL_LONGITUDE

    d = math.sqrt(3) * 70
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


def next_position():
    for point in SearchConfig.COVER:
        yield (point["lat"], point["lng"], 0)


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
    except:  # make sure we dont crash in the main loop
        log.error('Unexpected error while parsing response.')
        log.debug('Response dict: {}'.format(response_dict))
        consecutive_map_fails += 1
    else:
        global steps_completed
        steps_completed += 1
        log.info('Completed {:5.2f}% of scan.'.format(float(steps_completed) / num_steps * 100))


def search(api):
    global num_steps
    num_steps = len(SearchConfig.COVER)
    log.info("Starting scan of {} locations".format(num_steps))

    for i, next_pos in izip(count(start=1), next_position()):
        log.debug('Scanning step {:d} of {:d}.'.format(i, num_steps))
        log.debug('Scan location is {:f}, {:f}'.format(next_pos[0], next_pos[1]))

        # TODO: Add error throttle

        cell_ids = get_cell_ids(next_pos[0], next_pos[1])
        timestamps = [0, ] * len(cell_ids)
        api.get_map_objects(latitude=f2i(next_pos[0]),
                            longitude=f2i(next_pos[1]),
                            cell_id=cell_ids,
                            since_timestamp_ms=timestamps,
                            position=next_pos,
                            callback=callback)

        # Location change
        if SearchConfig.CHANGE:
            log.info("Changing scan location")
            SearchConfig.CHANGE = False
            api.empty_queue()

    api.wait_until_done()


def search_loop(args):
    global steps_completed
    api = PGoApi()
    api.add_workers(config['ACCOUNTS'])

    scan_start_time = 0

    while True:
        steps_completed = 0
        scan_start_time = time.time()
        search(api)
        SearchConfig.COMPLETE_SCAN_TIME = time.time() - scan_start_time
