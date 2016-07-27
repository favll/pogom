#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import sys
from threading import Thread

from pogom import config
from pogom.app import Pogom
from pogom.models import create_tables
from pogom.search import search_loop, set_cover, set_location, search_loop_async
from pogom.utils import get_args

log = logging.getLogger(__name__)


def start_locator_thread(args):
    if args.pycurl:
        search_thread = Thread(target=search_loop_async, args=(args,))
    else:
        search_thread = Thread(target=search_loop, args=(args,))

    search_thread.daemon = True
    search_thread.name = 'search_thread'
    search_thread.start()


if __name__ == '__main__':
    args = get_args()

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s [%(module)11s] [%(levelname)7s] %(message)s')
    if not args.debug:
        logging.getLogger("peewee").setLevel(logging.INFO)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("pogom.pgoapi.pgoapi").setLevel(logging.WARNING)
        logging.getLogger("pogom.pgoapi.rpc_api").setLevel(logging.WARNING)
        logging.getLogger("pogom.models").setLevel(logging.WARNING)
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
    elif args.debug == "info":
        logging.getLogger("pogom.pgoapi.pgoapi").setLevel(logging.INFO)
        logging.getLogger("pogom.models").setLevel(logging.INFO)
        logging.getLogger("werkzeug").setLevel(logging.INFO)
    elif args.debug == "debug":
        logging.getLogger("pogom.pgoapi.pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("pogom.pgoapi.pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("pogom.models").setLevel(logging.DEBUG)
        logging.getLogger("werkzeug").setLevel(logging.INFO)

    create_tables()

    set_location(args.location, args.radius)
    set_cover()

    start_locator_thread(args)

    app = Pogom(__name__)
    config['ROOT_PATH'] = app.root_path
    app.run(threaded=True, debug=args.debug, host=args.host, port=args.port)
