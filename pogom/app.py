#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask


class Pogom(Flask):
    def __init__(self, *args, **kwargs):
        super(Pogom, self).__init__(*args, **kwargs)
        self.route("/", methods=['GET'])(self.fullmap)
        self.route("/data", methods=['GET'])(self.data)

    def fullmap(self):
        pass

    def data(self):
        pass
