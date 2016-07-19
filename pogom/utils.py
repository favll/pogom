#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import getpass
import argparse


def parse_unicode(bytestring):
    decoded_string = bytestring.decode(sys.getfilesystemencoding())
    return decoded_string


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--auth-service',
                        type=str.lower, help='Auth Service', default='ptc')
    parser.add_argument('-u', '--username', help='Username', required=True)
    parser.add_argument('-p', '--password', help='Password', required=False)
    parser.add_argument('-l', '--location', type=parse_unicode,
                        help='Location', required=True)
    parser.add_argument('-st', '--step-limit', help='Steps', required=True)
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('-i', '--ignore',
                       help='Comma-separated list of Pokémon names or IDs to'
                       ' ignore')
    group.add_argument('-o', '--only',
                       help='Comma-separated list of Pokémon names or IDs to'
                       'search')
    parser.add_argument('-ar', '--auto_refresh',
                        help='Enables an autorefresh that behaves the same as'
                        ' a page reload. Needs an integer value for the amount'
                        ' of seconds')
    parser.add_argument('-dp', '--display-pokestops', help='Display pokéstops',
                        action='store_true', default=False)
    parser.add_argument('-dl', '--display-lured',
                        help='Display only lured pokéstop',
                        action='store_true', default=False)
    parser.add_argument('-dg', '--display-gyms', help='Display gyms',
                        action='store_true', default=False)
    parser.add_argument('-H', '--host', help='Set web server listening host',
                        default='127.0.0.1')
    parser.add_argument('-P', '--port', type=int,
                        help='Set web server listening port',
                        default=5000)
    parser.add_argument('-L', '--locale',
                        help='Locale for Pokemon names: default en, check'
                        'locale folder for more options',
                        default='en')
    parser.add_argument('-c', '--china',
                        help='Coordinates transformer for China',
                        action='store_true')
    parser.add_argument('-d', '--debug', help='Debug Mode',
                        action='store_true')

    args = parser.parse_args()
    if args.password is None:
        args.password = getpass.getpass()

    return args
