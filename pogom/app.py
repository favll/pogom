#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import calendar
from flask import Flask, jsonify, render_template, request
from flask.json import JSONEncoder
from datetime import datetime

from . import config
from .models import Pokemon, Gym, Pokestop

log = logging.getLogger(__name__)


class Pogom(Flask):
    def __init__(self, *args, **kwargs):
        super(Pogom, self).__init__(*args, **kwargs)
        self.json_encoder = CustomJSONEncoder
        self.route("/", methods=['GET'])(self.fullmap)
        self.route("/map-data", methods=['GET'])(self.map_data)

    def fullmap(self):
        return render_template('map.html',
                               lat=config['ORIGINAL_LATITUDE'],
                               lng=config['ORIGINAL_LONGITUDE'],
                               gmaps_key=config['GOOGLEMAPS_KEY'])

    def map_data(self):
        l = []
        if request.args.get('pokemons', 'all') == 'all':
            l.extend(Pokemon.get_active())
        
        if request.args.get('pokestops', 'none') == 'all':
            l.extend([p for p in Pokestop.select().dicts()])
        
        if request.args.get('pokestops', 'none') == 'lured':
            l.extend([p for p in Pokestop.select().dicts()]) #TODO
    
        if request.args.get('gyms', 'none') == 'all':
            l.extend([g for g in Gym.select().dicts()])
    
        return jsonify(l)


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
