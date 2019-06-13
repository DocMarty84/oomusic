# -*- coding: utf-8 -*

from odoo.addons.bus.controllers.main import BusController
from odoo.http import request


class MusicBusController(BusController):
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            channels = list(channels)
            channels.append((request.db, "oomusic.remote", request.session.uid))
        return super(MusicBusController, self)._poll(dbname, channels, last, options)
