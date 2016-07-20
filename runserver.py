#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

from threading import Thread

from pogom import config
from pogom.app import Pogom
from pogom.search import search_loop
from pogom.utils import get_args, insert_mock_data
from pogom.models import create_tables
from pogom.pgoapi.utilities import get_pos_by_name
from s2sphere import *

log = logging.getLogger(__name__)


def start_locator_thread(args):
    search_thread = Thread(target=search_loop, args=(args,))
    search_thread.daemon = True
    search_thread.name = 'search_thread'
    search_thread.start()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(module)11s] [%(levelname)7s] %(message)s')

    logging.getLogger("peewee").setLevel(logging.INFO)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("pogom.pgoapi.pgoapi").setLevel(logging.INFO)
    logging.getLogger("pogom.pgoapi.rpc_api").setLevel(logging.CRITICAL)

    args = get_args()
    create_tables()
    
    position = get_pos_by_name(args.location)
    log.info('Parsed location is: {:.4f}/{:.4f}/{:.4f} (lat/lng/alt)'.
             format(*position))

    config['ORIGINAL_LATITUDE'] = position[0]
    config['ORIGINAL_LONGITUDE'] = position[1]
    
    coords = LatLng(math.radians(position[0]), math.radians(position[1]))
    cap = Cap.from_axis_height(coords.to_point(), 0.00000001)
    log.info(str(coords))

    coverer = RegionCoverer()
    coverer.min_level = 15
    coverer.max_level = 15
    coverer.max_cells = 200

    cover = [ Cell(cell_id) for cell_id in coverer.get_covering(cap)]
    config['COVER'] = cover


    if not args.mock:
        start_locator_thread(args)
    else:
        insert_mock_data(config, 6)

    app = Pogom(__name__)
    config['ROOT_PATH'] = app.root_path
    app.run(threaded=True, debug=args.debug, host=args.host, port=args.port)
