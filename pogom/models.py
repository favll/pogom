#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import random
import math
from peewee import Model, SqliteDatabase, InsertQuery, IntegerField, \
    CharField, FloatField, BooleanField, DateTimeField, fn, SQL
from datetime import datetime
from base64 import b64encode
import threading

from .utils import get_pokemon_name, get_args
from playhouse.db_url import connect


args = get_args()

if args.db != 'sqlite':
    db = connect(args.db)
else:
    db = SqliteDatabase('pogom.db', pragmas=(
        ('journal_mode', 'WAL'),
        ('cache_size', 10000),
        ('mmap_size', 1024 * 1024 * 32),
    ))

log = logging.getLogger(__name__)
lock = threading.Lock()


class BaseModel(Model):
    class Meta:
        database = db

    @classmethod
    def get_all(cls):
        return [m for m in cls.select().dicts()]


class Pokemon(BaseModel):
    # We are base64 encoding the ids delivered by the api
    # because they are too big for sqlite to handle
    encounter_id = CharField(primary_key=True)
    spawnpoint_id = CharField()
    pokemon_id = IntegerField()
    latitude = FloatField()
    longitude = FloatField()
    disappear_time = DateTimeField()

    @classmethod
    def get_active(cls):
        query = (Pokemon
                 .select()
                 .where(Pokemon.disappear_time > datetime.utcnow())
                 .dicts())

        pokemons = []
        for p in query:
            p['pokemon_name'] = get_pokemon_name(p['pokemon_id'])
            pokemons.append(p)

        return pokemons

    @classmethod
    def get_stats(cls):
        query = (Pokemon
                 .select(Pokemon.pokemon_id, fn.COUNT(Pokemon.pokemon_id).alias('count'), fn.MAX(Pokemon.disappear_time).alias('lastseen'))
                 .group_by(Pokemon.pokemon_id)
                 .order_by(-SQL('count'))
                 .dicts())

        pokemons = list(query)

        known_pokemon = set( p['pokemon_id'] for p in query )
        unknown_pokemon = set(range(1,151)).difference(known_pokemon)
        pokemons.extend( { 'pokemon_id': i, 'count': 0, 'lastseen': None } for i in unknown_pokemon)

        for p in pokemons:
            p['pokemon_name'] = get_pokemon_name(p['pokemon_id'])
        return pokemons

    @classmethod
    def get_heat_stats(cls):
        query = (Pokemon
                 .select(Pokemon.pokemon_id, fn.COUNT(Pokemon.pokemon_id).alias('count'), Pokemon.latitude, Pokemon.longitude)
                 .group_by(Pokemon.latitude, Pokemon.longitude, Pokemon.pokemon_id)
                 .order_by(-SQL('count'))
                 .dicts())

        pokemons = list(query)

        known_pokemon = set(p['pokemon_id'] for p in query)
        unknown_pokemon = set(range(1, 151)).difference(known_pokemon)
        pokemons.extend({'pokemon_id': i, 'count': 0} for i in unknown_pokemon)
        for p in pokemons:
            p['pokemon_name'] = get_pokemon_name(p['pokemon_id'])

        return pokemons

class Pokestop(BaseModel):
    pokestop_id = CharField(primary_key=True)
    enabled = BooleanField()
    latitude = FloatField()
    longitude = FloatField()
    last_modified = DateTimeField()
    lure_expiration = DateTimeField(null=True)
    active_pokemon_id = IntegerField(null=True)


class Gym(BaseModel):
    UNCONTESTED = 0
    TEAM_MYSTIC = 1
    TEAM_VALOR = 2
    TEAM_INSTINCT = 3

    gym_id = CharField(primary_key=True)
    team_id = IntegerField()
    guard_pokemon_id = IntegerField(null=True)
    gym_points = IntegerField()
    enabled = BooleanField()
    latitude = FloatField()
    longitude = FloatField()
    last_modified = DateTimeField()


def parse_map(map_dict):
    pokemons = {}
    pokestops = {}
    gyms = {}

    cells = map_dict['responses']['GET_MAP_OBJECTS']['map_cells']
    if sum(len(cell.keys()) for cell in cells) == len(cells) * 2:
        log.warning("Received valid response but without any data. Possibly rate-limited?")

    for cell in cells:
        for p in cell.get('wild_pokemons', []):
            if p['encounter_id'] in pokemons:
                continue  # prevent unnecessary parsing

            pokemons[p['encounter_id']] = {
                'encounter_id': b64encode(str(p['encounter_id'])),
                'spawnpoint_id': p['spawn_point_id'],
                'pokemon_id': p['pokemon_data']['pokemon_id'],
                'latitude': p['latitude'],
                'longitude': p['longitude'],
                'disappear_time': datetime.utcfromtimestamp(
                        (p['last_modified_timestamp_ms'] +
                         p['time_till_hidden_ms']) / 1000.0)
            }
            if p['time_till_hidden_ms'] < 0 or p['time_till_hidden_ms'] > 900000:
                pokemons[p['encounter_id']]['disappear_time'] = datetime.utcfromtimestamp(
                        p['last_modified_timestamp_ms']/1000 + 15*60)

        for p in cell.get('catchable_pokemons', []):
            if p['encounter_id'] in pokemons:
                continue  # prevent unnecessary parsing

            log.critical("found catchable pokemon not in wild: {}".format(p))

            pokemons[p['encounter_id']] = {
                'encounter_id': b64encode(str(p['encounter_id'])),
                'spawnpoint_id': p['spawn_point_id'],
                'pokemon_id': p['pokemon_data']['pokemon_id'],
                'latitude': p['latitude'],
                'longitude': p['longitude'],
                'disappear_time': datetime.utcfromtimestamp(
                        (p['last_modified_timestamp_ms'] +
                         p['time_till_hidden_ms']) / 1000.0)
            }

        for f in cell.get('forts', []):
            if f['id'] in gyms or f['id'] in pokestops:
                continue  # prevent unnecessary parsing

            if f.get('type') == 1:  # Pokestops
                if 'lure_info' in f:
                    lure_expiration = datetime.utcfromtimestamp(
                            f['lure_info']['lure_expires_timestamp_ms'] / 1000.0)
                    active_pokemon_id = f['lure_info']['active_pokemon_id']
                else:
                    lure_expiration, active_pokemon_id = None, None

                pokestops[f['id']] = {
                    'pokestop_id': f['id'],
                    'enabled': f['enabled'],
                    'latitude': f['latitude'],
                    'longitude': f['longitude'],
                    'last_modified': datetime.utcfromtimestamp(
                            f['last_modified_timestamp_ms'] / 1000.0),
                    'lure_expiration': lure_expiration,
                    'active_pokemon_id': active_pokemon_id
                }

            else:  # Currently, there are only stops and gyms
                gyms[f['id']] = {
                    'gym_id': f['id'],
                    'team_id': f.get('owned_by_team', 0),
                    'guard_pokemon_id': f.get('guard_pokemon_id', None),
                    'gym_points': f.get('gym_points', 0),
                    'enabled': f['enabled'],
                    'latitude': f['latitude'],
                    'longitude': f['longitude'],
                    'last_modified': datetime.utcfromtimestamp(
                            f['last_modified_timestamp_ms'] / 1000.0),
                }

    with db.atomic() and lock:
        if pokemons:
            log.info("Upserting {} pokemon".format(len(pokemons)))
            bulk_upsert(Pokemon, pokemons)

        if pokestops:
            log.info("Upserting {} pokestops".format(len(pokestops)))
            bulk_upsert(Pokestop, pokestops)

        if gyms:
            log.info("Upserting {} gyms".format(len(gyms)))
            bulk_upsert(Gym, gyms)


def bulk_upsert(cls, data):
    num_rows = len(data.values())
    i = 0
    step = 100

    while i < num_rows:
        log.debug("Inserting items {} to {}".format(i, min(i + step, num_rows)))
        InsertQuery(cls, rows=data.values()[i:min(i + step, num_rows)]).upsert().execute()
        i += step


def create_tables():
    db.connect()
    db.create_tables([Pokemon, Pokestop, Gym], safe=True)
    db.close()
