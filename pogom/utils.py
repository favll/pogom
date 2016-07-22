#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import getpass
import argparse
import re
import uuid
import os
import json
import math
from datetime import datetime, timedelta
import s2sphere as s2

from . import config


def parse_unicode(bytestring):
    decoded_string = bytestring.decode(sys.getfilesystemencoding())
    return decoded_string


def get_args():
    # fuck PEP8
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--auth-service', type=str.lower, help='Auth Service [ptc|google]', default='ptc')
    parser.add_argument('-u', '--username', help='Username', required=True)
    parser.add_argument('-p', '--password', help='Password', required=False)
    parser.add_argument('-l', '--location', type=parse_unicode, help='Location, address or coordinates', required=True)
    parser.add_argument('-r', '--radius', help='Search radius [m]', required=True, type=int)
    #group = parser.add_mutually_exclusive_group(required=False)
    parser.add_argument('-H', '--host', help='Set web server listening host', default='127.0.0.1')
    parser.add_argument('-P', '--port', type=int, help='Set web server listening port', default=5000)
    parser.add_argument('-L', '--locale', help='Locale for Pokemon names: default en, check '
                        'locale folder for more options', default='en')
    parser.add_argument('-c', '--china', help='Coordinates transformer for China', action='store_true')
    parser.add_argument('-d', '--debug', type=str.lower, help='Debug Level [info|debug]', default=None)
    parser.add_argument('-m', '--mock', help='Mock mode. Starts the web server but not the background thread.', action='store_true', default=False)

    args = parser.parse_args()
    if args.password is None:
        args.password = getpass.getpass()

    return args


def insert_mock_data(config, num_pokemons):
    from .models import Pokemon
    from .search import generate_location_steps

    locations = [l for l
                 in generate_location_steps(
                    SearchConfig.ORIGINAL_LATITUDE,
                    SearchConfig.ORIGINAL_LONGITUDE,
                    num_pokemons)]
    disappear_time = datetime.now() + timedelta(hours=1)

    for i in xrange(num_pokemons):
        Pokemon.create(encounter_id=uuid.uuid4(),
                       spawnpoint_id='sp{}'.format(i),
                       pokemon_id=(i+1) % 150,
                       latitude=locations[i][0],
                       longitude=locations[i][1],
                       disappear_time=disappear_time)


def get_pokemon_name(pokemon_id):
    if not hasattr(get_pokemon_name, 'names'):
        file_path = os.path.join(
            config['ROOT_PATH'],
            config['LOCALES_DIR'],
            'pokemon.{}.json'.format(config['LOCALE']))

        with open(file_path, 'r') as f:
            get_pokemon_name.names = json.loads(f.read())

    return get_pokemon_name.names[str(pokemon_id)]
