#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import random
import math
from peewee import Model, SqliteDatabase, InsertQuery, IntegerField, \
    CharField, FloatField, BooleanField, DateTimeField, fn, SQL
from datetime import datetime
from base64 import b64encode
from sys import maxint
from geographiclib.geodesic import Geodesic
from pgoapi.utilities import get_pos_by_name

from .utils import get_pokemon_name

db = SqliteDatabase('pogom.db', pragmas=(
    ('journal_mode', 'WAL'),
    ('cache_size', 10000),
    ('mmap_size', 1024 * 1024 * 32),
))
log = logging.getLogger(__name__)


class SearchConfig(object):
    ORIGINAL_LATITUDE = None
    ORIGINAL_LONGITUDE = None
    COVER = None
    RADIUS = None

    SCAN_LOCATIONS = {}

    CHANGE = False  # Triggered when the setup is changed due to user input

    LOGGED_IN = 0.0
    LAST_SUCCESSFUL_REQUEST = 0.0
    COMPLETE_SCAN_TIME = 0

    @classmethod
    def update_scan_locations(cls, scan_locations):
        location_names = set([])
        # Add new locations
        for scan_location in scan_locations:

            if scan_location['location'] not in cls.SCAN_LOCATIONS:
                lat, lng, alt = get_pos_by_name(scan_location['location'])
                log.info('Parsed location is: {:.4f}/{:.4f}/{:.4f} '
                         '(lat/lng/alt)'.format(lat, lng, alt))
                scan_location['latitude'] = lat
                scan_location['longitude'] = lng
                scan_location['altitude'] = alt
                cls.SCAN_LOCATIONS[scan_location['location']] = scan_location
            location_names.add(scan_location['location'])

        # Remove old locations
        for location_name in cls.SCAN_LOCATIONS:
            if location_name not in location_names:
                del cls.SCAN_LOCATIONS[location_name]

        cls._update_cover()

    @classmethod
    def add_scan_location(cls, lat, lng, radius):
        scan_location = {
            'location': '{},{}'.format(lat, lng),
            'latitude': lat,
            'longitude': lng,
            'altitude': 0,
            'radius': radius
        }

        cls.SCAN_LOCATIONS[scan_location['location']] = scan_location
        cls._update_cover()

    @classmethod
    def delete_scan_location(cls, lat, lng):
        for k, v in cls.SCAN_LOCATIONS.iteritems():
            if v['latitude'] == lat and v['longitude'] == lng:
                del cls.SCAN_LOCATIONS[k]
                cls._update_cover()
                return

    @classmethod
    def _update_cover(cls):
        cover = []
        for scan_location in cls.SCAN_LOCATIONS.values():
            lat = scan_location["latitude"]
            lng = scan_location["longitude"]
            radius = scan_location["radius"]

            d = math.sqrt(3) * 70
            points = [[{'lat2': lat, 'lon2': lng, 's': 0}]]

            # The lines below are magic. Don't touch them.
            for i in xrange(1, maxint):
                oor_counter = 0

                points.append([])
                for j in range(0, 6 * i):
                    p = points[i - 1][(j - j / i - 1 + (j % i == 0))]
                    p_new = Geodesic.WGS84.Direct(p['lat2'], p['lon2'], (j+i-1)/i * 60, d)
                    p_new['s'] = Geodesic.WGS84.Inverse(p_new['lat2'], p_new['lon2'], lat, lng)['s12']
                    points[i].append(p_new)

                    if p_new['s'] > radius:
                        oor_counter += 1

                if oor_counter == 6 * i:
                    break

            cover.extend({"lat": p['lat2'], "lng": p['lon2']}
                         for sublist in points for p in sublist if p['s'] < radius)

        random.shuffle(cover)  # Shuffles list in-place
        cls.COVER = cover


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
                 .select(Pokemon.pokemon_id, fn.COUNT(Pokemon.pokemon_id).alias('count'))
                 .group_by(Pokemon.pokemon_id)
                 .order_by(-SQL('count'))
                 .dicts())

        pokemons = list(query)

        known_pokemon = set( p['pokemon_id'] for p in query )
        unknown_pokemon = set(range(1,151)).difference(known_pokemon)
        pokemons.extend( { 'pokemon_id': i, 'count': 0 } for i in unknown_pokemon)

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

    with db.atomic():
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
