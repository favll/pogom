#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import getpass
import json
import os
import sys
import uuid
from datetime import datetime, timedelta

from . import config


def parse_unicode(bytestring):
    decoded_string = bytestring.decode(sys.getfilesystemencoding())
    return decoded_string


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--auth-service', type=str.lower, help='Auth Service [ptc|google]', default='ptc')
    parser.add_argument('-u', '--username', help='Username', required=True)
    parser.add_argument('-p', '--password', help='Password', required=False)

    parser.add_argument('-l', '--location', type=parse_unicode, help='Location, address or coordinates', required=True)
    parser.add_argument('-r', '--radius', help='Search radius [m]', required=True, type=int)

    parser.add_argument('-H', '--host', help='Set web server listening host', default='127.0.0.1')
    parser.add_argument('-P', '--port', type=int, help='Set web server listening port', default=5000)

    parser.add_argument('-d', '--debug', type=str.lower, help='Debug Level [info|debug]', default=None)
    parser.add_argument('-c', '--pycurl', help='Use pycurl downloader (unstable)')

    args = parser.parse_args()
    if args.password is None:
        args.password = getpass.getpass()

    return args


def get_pokemon_name(pokemon_id):
    if not hasattr(get_pokemon_name, 'names'):
        file_path = os.path.join(
                config['ROOT_PATH'],
                config['LOCALES_DIR'],
                'pokemon.{}.json'.format(config['LOCALE']))

        with open(file_path, 'r') as f:
            get_pokemon_name.names = json.loads(f.read())

    return get_pokemon_name.names[str(pokemon_id)]
