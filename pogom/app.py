#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, jsonify, render_template
from pogom.models import Pokemon, Gym, Pokestop


class Pogom(Flask):
    def __init__(self, *args, **kwargs):
        super(Pogom, self).__init__(*args, **kwargs)
        self.route("/", methods=['GET'])(self.fullmap)
        self.route("/pokemons", methods=['GET'])(self.pokemons)
        self.route("/gyms", methods=['GET'])(self.gyms)
        self.route("/pokestops", methods=['GET'])(self.pokestops)

    def fullmap(self):
        return render_template('map.html', lat=6.0, lng=7.0)

    def pokemons(self):
        return jsonify([p for p in Pokemon.get_active()])

    def pokestops(self):
        return jsonify([p for p in Pokestop.select().dicts()])

    def gyms(self):
        return jsonify([g for g in Gym.select().dicts()])
