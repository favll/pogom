#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import math
import time
import collections
import cProfile
import os
import json
import random
from datetime import datetime
from itertools import izip, count

from pgoapi import PGoApi
from pgoapi.utilities import f2i, get_cell_ids
from .models import parse_map, SearchConfig
from . import config

log = logging.getLogger(__name__)

consecutive_map_fails = 0
steps_completed = 0
num_steps = 0


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
        log.error('Response dict: {}'.format(response_dict))
        consecutive_map_fails += 1
    else:
        global steps_completed
        steps_completed += 1
        log.info('Completed {:5.2f}% of scan.'.format(float(steps_completed) / num_steps * 100))


def search(api):
    global num_steps
    num_steps = len(SearchConfig.COVER)
    log.info("Starting scan of {} locations".format(num_steps))

    for i, next_pos in enumerate(next_position()):
        log.debug('Scanning step {:d} of {:d}.'.format(i, num_steps))
        log.debug('Scan location is {:f}, {:f}'.format(next_pos[0], next_pos[1]))

        # TODO: Add error throttle

        cell_ids = get_cell_ids(next_pos[0], next_pos[1], radius=70)
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


def search_loop():
    global steps_completed
    _update_cover()

    api = PGoApi()
    num_workers = min(int(math.ceil(len(config['ACCOUNTS']) / 23.0)), 3)
    api.create_workers(num_workers)
    api.add_accounts(config['ACCOUNTS'])

    scan_start_time = 0

    while True:
        steps_completed = 0
        scan_start_time = time.time()
        search(api)
        SearchConfig.COMPLETE_SCAN_TIME = time.time() - scan_start_time
