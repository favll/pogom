#!/usr/bin/python
# -*- coding: utf-8 -*-

from peewee import *  # Change this

db = SqliteDatabase('pogom.db')


class BaseModel(Model):
    class Meta:
        database = db


class Pokemon(BaseModel):
    encounter_id = IntegerField(primary_key=True)
    spawnpoint_id = CharField()
    pokemon_id = IntegerField()
    latitude = FloatField()
    longitude = FloatField()
    disappear_time = DateTimeField()


class Pokestop(BaseModel):
    pokestop_id = CharField(unique=True)
    latitude = FloatField()
    longitude = FloatField()


class Gym(BaseModel):
    UNCONTESTED = 0
    TEAM_MYSTIC = 1
    TEAM_VALOR = 2
    TEAM_INSTINCT = 3

    gym_id = CharField(unique=True)
    team_id = IntegerField()
    team_name = CharField()
    lat = FloatField()
    lon = FloatField()


def create_tables():
    db.connect()
    db.create_tables([Pokemon, Pokestop, Gym], safe=True)
    db.close()
