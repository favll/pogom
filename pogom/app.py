#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import calendar
from flask import Flask, jsonify, render_template, request, abort
from flask.json import JSONEncoder
from datetime import datetime
import time

from . import config
from .models import Pokemon, Gym, Pokestop, SearchConfig
from .search import set_cover

log = logging.getLogger(__name__)


class Pogom(Flask):
    def __init__(self, *args, **kwargs):
        super(Pogom, self).__init__(*args, **kwargs)
        self.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
        self.json_encoder = CustomJSONEncoder

        self.route('/', methods=['GET'])(self.fullmap)
        self.route('/map-data', methods=['GET'])(self.map_data)
        self.route('/cover', methods=['GET'])(self.cover)
        self.route('/set-location', methods=['POST'])(self.set_location)
        self.route('/stats', methods=['GET'])(self.stats)

    def fullmap(self):
        return render_template('map.html',
                               lat=SearchConfig.ORIGINAL_LATITUDE,
                               lng=SearchConfig.ORIGINAL_LONGITUDE,
                               gmaps_key=config['GOOGLEMAPS_KEY'])

    def map_data(self):
        d = {}

        if not SearchConfig.LAST_SUCCESSFUL_REQUEST:
            time_since_last_req = "na"
        elif SearchConfig.LAST_SUCCESSFUL_REQUEST == -1:
            time_since_last_req = "sleep"
        else:
            time_since_last_req = time.time() - SearchConfig.LAST_SUCCESSFUL_REQUEST

        d['server_status'] = {'login_time': SearchConfig.LOGGED_IN,
                              'last-successful-request': time_since_last_req,
                              'complete-scan-time': SearchConfig.COMPLETE_SCAN_TIME}
        d['search_area'] = {'lat': SearchConfig.ORIGINAL_LATITUDE,
                            'lng': SearchConfig.ORIGINAL_LONGITUDE,
                            'radius': SearchConfig.RADIUS}

        if request.args.get('pokemon', 'true') == 'true':
            d['pokemons'] = Pokemon.get_active()

        if request.args.get('pokestops', 'false') == 'true':
            d['pokestops'] = Pokestop.get_all()

        # TODO: Lured pokestops

        if request.args.get('gyms', 'true') == 'true':
            d['gyms'] = Gym.get_all()

        return jsonify(d)

    def cover(self):
        return jsonify({'cover': SearchConfig.COVER,
                        'center': {'lat': SearchConfig.ORIGINAL_LATITUDE,
                                   'lng': SearchConfig.ORIGINAL_LONGITUDE}})

    def set_location(self):
        lat = request.values.get('lat', type=float)
        lng = request.values.get('lng', type=float)

        if not (lat and lng):
            abort(400)

        SearchConfig.ORIGINAL_LATITUDE = lat
        SearchConfig.ORIGINAL_LONGITUDE = lng
        set_cover()
        SearchConfig.CHANGE = True

        return ('', 204)

    def stats(self):
        stats = Pokemon.get_stats()
        count = sum(p['count'] for p in stats)
        return render_template('stats.html', pokemons=Pokemon.get_stats(), total=count)


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
