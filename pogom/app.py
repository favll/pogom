#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import calendar
from flask import Flask, jsonify, render_template, request, abort, redirect, url_for, make_response
from flask.json import JSONEncoder
from datetime import datetime
import time
import json
import threading
import random
import string
import os

from . import config
from .models import Pokemon, Gym, Pokestop
from .scan import ScanMetrics, Scanner
from .utils import get_locale

log = logging.getLogger(__name__)


class Pogom(Flask):
    def __init__(self, scan_config, *args, **kwargs):
        super(Pogom, self).__init__(*args, **kwargs)
        self.scan_config = scan_config

        self.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
        self.json_encoder = CustomJSONEncoder

        self.route('/', methods=['GET'])(self.fullmap)
        self.route('/heatmap-data', methods=['GET'])(self.heatmap_data)
        self.route('/map-data', methods=['GET'])(self.map_data)
        self.route('/cover', methods=['GET'])(self.cover)
        self.route('/location', methods=['POST'])(self.add_location)
        self.route('/location', methods=['DELETE'])(self.delete_location)
        self.route('/stats', methods=['GET'])(self.stats)
        self.route('/config', methods=['GET'])(self.get_config_site)
        self.route('/config', methods=['POST'])(self.post_config_site)
        self.route('/login', methods=['GET', 'POST'])(self.login)
        self.route('/locale', methods=['GET'])(self.locale)

    def is_authenticated(self):
        if config.get('CONFIG_PASSWORD', None) and not request.cookies.get("auth") == config['AUTH_KEY']:
            return False
        else:
            return True

    def fullmap(self):
        # if 'search_thread' not in [t.name for t in threading.enumerate()]:
        if (not config.get('GOOGLEMAPS_KEY', None) or
                not config.get('ACCOUNTS', None)):
            return redirect(url_for('get_config_site'))

        return render_template('map.html',
                               scan_locations=json.dumps(self.scan_config.SCAN_LOCATIONS.values()),
                               gmaps_key=config['GOOGLEMAPS_KEY'],
                               is_authenticated=self.is_authenticated())

    def login(self):
        if self.is_authenticated():
            return redirect(url_for('get_config_site'))

        if request.method == "GET":
            return render_template('login.html')
        if request.form.get('password', None) == config.get('CONFIG_PASSWORD', None):
            resp = make_response(redirect(url_for('get_config_site')))
            resp.set_cookie('auth', config['AUTH_KEY'])
            return resp

    def heatmap_data(self):
        return jsonify( Pokemon.get_heat_stats() )

    def get_config_site(self):
        if not self.is_authenticated():
            return redirect(url_for('login'))

        return render_template(
            'config.html',
            locale=config.get('LOCALE', ''),
            locales_available=config.get('LOCALES_AVAILABLE', []),
            gmaps_key=config.get('GOOGLEMAPS_KEY', None),
            accounts=config.get('ACCOUNTS', []),
            password=config.get('CONFIG_PASSWORD', None))

    def post_config_site(self):
        if not self.is_authenticated():
            return redirect(url_for('login'))

        config['LOCALE'] = request.form.get('locale', 'en')
        config['GOOGLEMAPS_KEY'] = request.form.get('gmapsKey', '')

        pw = request.form.get('configPassword', None)
        pw_changed = (pw != config.get('CONFIG_PASSWORD', None))
        if pw_changed:
            config['CONFIG_PASSWORD'] = pw
            config['AUTH_KEY'] = ''.join(random.choice(string.lowercase) for _ in range(32))

        accounts_str = request.form.get('accounts', None)

        usernames_before = set([])
        for account in config.get('ACCOUNTS', []):
            usernames_before.add(account['username'])

        usernames = set([])
        accounts_parsed = []
        if accounts_str:
            for a in accounts_str.splitlines():
                a = a.split(":")
                if (len(a) == 2) and (a[0].strip() not in usernames):
                    accounts_parsed.append({'username': a[0].strip(), 'password': a[1].strip()})
                    usernames.add(a[0].strip())

        config['ACCOUNTS'] = accounts_parsed
        self.scan_config.ACCOUNTS_CHANGED = (usernames_before != usernames)
        self.save_config()

        self.scan_config.RESTART = True

        resp = make_response(render_template(
            'config.html',
            locale=config.get('LOCALE', ''),
            locales_available=config.get('LOCALES_AVAILABLE', []),
            gmaps_key=config.get('GOOGLEMAPS_KEY', None),
            accounts=config.get('ACCOUNTS', []),
            password=config.get('CONFIG_PASSWORD', None),
            alert=True))
        if pw_changed:
            resp.set_cookie('auth', config['AUTH_KEY'])

        return resp

    def save_config(self):
        if not self.is_authenticated():
            return redirect(url_for('login'))

        if (config['CONFIG_PATH'] is not None and
                os.path.isfile(config['CONFIG_PATH'])):
            config_path = config['CONFIG_PATH']
        else:
            config_path = os.path.join(config['ROOT_PATH'], 'config.json')

        with open(config_path, 'w') as f:
            data = {'GOOGLEMAPS_KEY': config['GOOGLEMAPS_KEY'],
                    'LOCALE': config['LOCALE'],
                    'CONFIG_PASSWORD': config['CONFIG_PASSWORD'],
                    'SCAN_LOCATIONS': self.scan_config.SCAN_LOCATIONS.values(),
                    'ACCOUNTS': config['ACCOUNTS']}
            f.write(json.dumps(data))

    def map_data(self):
        d = {}

        if not ScanMetrics.LAST_SUCCESSFUL_REQUEST:
            time_since_last_req = "na"
        elif ScanMetrics.LAST_SUCCESSFUL_REQUEST == -1:
            time_since_last_req = "sleep"
        else:
            time_since_last_req = time.time() - ScanMetrics.LAST_SUCCESSFUL_REQUEST

        d['server_status'] = {'num-threads': ScanMetrics.NUM_THREADS,
                              'num-accounts': ScanMetrics.NUM_ACCOUNTS,
                              'last-successful-request': time_since_last_req,
                              'complete-scan-time': ScanMetrics.COMPLETE_SCAN_TIME,
                              'current-scan-percent': ScanMetrics.CURRENT_SCAN_PERCENT}

        d['scan_locations'] = self.scan_config.SCAN_LOCATIONS

        if request.args.get('pokemon', 'true') == 'true':
            d['pokemons'] = Pokemon.get_active()

        if request.args.get('pokestops', 'false') == 'true':
            d['pokestops'] = Pokestop.get_all()

        # TODO: Lured pokestops

        if request.args.get('gyms', 'true') == 'true':
            d['gyms'] = Gym.get_all()

        return jsonify(d)

    def cover(self):
        return jsonify({'cover': self.scan_config.COVER,
                        'scan_locations': self.scan_config.SCAN_LOCATIONS.values()})

    def add_location(self):
        if not self.is_authenticated():
            return redirect(url_for('login'))

        lat = request.values.get('lat', type=float)
        lng = request.values.get('lng', type=float)
        radius = request.values.get('radius', type=int)

        if not (lat and lng and radius):
            abort(400)

        self.scan_config.add_scan_location(lat, lng, radius)
        self.save_config()

        return ('', 204)

    def delete_location(self):
        if not self.is_authenticated():
            return redirect(url_for('login'))

        lat = request.values.get('lat', type=float)
        lng = request.values.get('lng', type=float)

        if not (lat and lng):
            abort(400)

        self.scan_config.delete_scan_location(lat, lng)
        self.save_config()

        return ('', 204)

    def stats(self):
        stats = Pokemon.get_stats()
        count = sum(p['count'] for p in stats)
        return render_template('stats.html', pokemons=stats, total=count)

    def locale(self):
        return jsonify(get_locale())


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, datetime):
                if obj.utcoffset() is not None:
                    obj = obj - obj.utcoffset()
                millis = int(
                        calendar.timegm(obj.timetuple()) * 1000 +
                        obj.microsecond / 1000
                )
                return millis
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)
