#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import calendar
from flask import Flask, jsonify, render_template, request
from flask.json import JSONEncoder
from datetime import datetime
import time

from . import config
from .models import Pokemon, Gym, Pokestop, SearchConfig

log = logging.getLogger(__name__)


class Pogom(Flask):
    def __init__(self, *args, **kwargs):
        super(Pogom, self).__init__(*args, **kwargs)
        self.json_encoder = CustomJSONEncoder
        self.route('/', methods=['GET'])(self.fullmap)
        self.route('/map-data', methods=['GET'])(self.map_data)
        self.route('/cover', methods=['GET'])(self.cover)

    def fullmap(self):
        return render_template('map.html',
                               lat=SearchConfig.ORIGINAL_LATITUDE,
                               lng=SearchConfig.ORIGINAL_LONGITUDE,
                               gmaps_key=config['GOOGLEMAPS_KEY'])

    def map_data(self):
        d = {}
        d['server_status'] = {'login_time': SearchConfig.LOGGED_IN,
                              'last-successful-request': SearchConfig.LAST_SUCCESSFUL_REQUEST - time.time()}
        
        if request.args.get('pokemon', 'true') == 'true':
            d['pokemons'] = Pokemon.get_active()

        if request.args.get('pokestops', 'false') == 'true':
            d['pokestops'] = Pokestop.get_all()

        # TODO: Lured pokestops

        if request.args.get('gyms', 'true') == 'true':
            d['gyms'] = Gym.get_all()

        return jsonify(d)

    def cover(self):
        return jsonify(SearchConfig.COVER)
        


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
