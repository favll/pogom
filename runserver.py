#!/usr/bin/python
# -*- coding: utf-8 -*-

from threading import Thread

from pogom.app import Pogom
from pogom.search import search
from pogom.utils import get_args
from pogom.models import create_tables


def start_locator_thread(args):
    search_thread = Thread(target=search, args=(args,))
    search_thread.daemon = True
    search_thread.name = 'search_thread'
    search_thread.start()


if __name__ == '__main__':
    args = get_args()
    print args
    create_tables()
    start_locator_thread(args)

    app = Pogom(__name__)
    app.run()
