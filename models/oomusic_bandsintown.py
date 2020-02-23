# -*- coding: utf-8 -*-

import datetime
import hashlib
import json
import logging
import operator as op
import time
from math import asin, cos, radians, sin, sqrt

import requests
from werkzeug.urls import url_fix

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

SYMBOL_NAME_MAP = {"<": "lt", "<=": "le", "=": "eq", "!=": "ne", ">=": "ge", ">": "gt"}


class MusicBandsintown(models.Model):
    _name = "oomusic.bandsintown"
    _description = "BandsInTown Cache Management"

    name = fields.Char("URL Hash", index=True, required=True)
    url = fields.Char("URL", required=True)
    content = fields.Char("Result", required=True)
    expiry_date = fields.Datetime("Expiry Date", required=True)
    removal_date = fields.Datetime("Removal Date", required=True)

    _sql_constraints = [
        ("oomusic_bandsintown_name_uniq", "unique(name)", "URL hash must be unique!")
    ]

    def get_query(self, url, sleep=0.0, force=False):
        # Get BandsInTown key and cache duration
        ConfigParam = self.env["ir.config_parameter"].sudo()
        bit_key = ConfigParam.get_param("oomusic.bandsintown_key")
        bit_cache = int(ConfigParam.get_param("oomusic.bandsintown_cache", 14))
        ext_info = ConfigParam.get_param("oomusic.ext_info", "auto")
        if not bit_key:
            return "{}"

        url = url_fix("{}?app_id={}&date=upcoming".format(url, bit_key)).encode("utf-8")
        url_hash = hashlib.sha1(url).hexdigest()

        Bandsintown = self.search([("name", "=", url_hash)])
        if force or not Bandsintown or Bandsintown.expiry_date < fields.Datetime.now():
            content = "{}"
            if ext_info == "manual" and not force:
                content = Bandsintown.content or content
                return content
            try:
                time.sleep(sleep)
                r = requests.get(url, timeout=3.0)
                if r.status_code == 200:
                    content = r.content.decode("utf-8")
            except:
                _logger.warning('Error while fetching URL "%s"', url, exc_info=True)

            expiry_date = datetime.datetime.utcnow() + datetime.timedelta(days=bit_cache)
            removal_date = datetime.datetime.utcnow() + datetime.timedelta(days=bit_cache + 14)

            # Save in cache
            if not Bandsintown:
                writer = self.create
            else:
                writer = self.write
            writer(
                {
                    "name": url_hash,
                    "url": url,
                    "content": content,
                    "expiry_date": expiry_date,
                    "removal_date": removal_date,
                }
            )

        else:
            content = Bandsintown.content or "{}"

        return content

    @api.model
    def cron_build_bandsintown_cache(self):
        # Build cache for artists. Limit to 200 artists chosen randomly to avoid running for
        # unexpectedly long periods of time.
        self.env.cr.execute(
            """
            SELECT a.id
            FROM oomusic_artist a
            JOIN oomusic_preference AS p ON a.id = p.res_id
            WHERE p.bit_follow = 'done'
                AND p.res_model = 'oomusic.artist'
            ORDER BY RANDOM()
            LIMIT 200
        """
        )
        cache = {}
        for artist in self.env["oomusic.artist"].browse([r[0] for r in self.env.cr.fetchall()]):
            _logger.debug("Getting Bandsintown cache for artist '%s'...", artist.name)
            cache[(artist.id, artist.name)] = artist._bandsintown_artist_getevents(sleep=0.5)

        # Create the events
        self.env["oomusic.bandsintown.event"]._create_from_cache(cache)

        # Clean-up outdated entries
        self.search([("removal_date", "<", fields.Datetime.now())]).unlink()
        self.env["oomusic.bandsintown.event"].search(
            [("date_event", "<", fields.Date.context_today(self))]
        ).write({"active": False})


class MusicBandsintownEvent(models.Model):
    _name = "oomusic.bandsintown.event"
    _description = "BandsInTown Events"
    _order = "date_event"

    name = fields.Char("BandsInTown ID", index=True, required=True)
    date_event = fields.Date("Date")
    country = fields.Char("Country")
    region = fields.Char("Region")
    city = fields.Char("City")
    location = fields.Char("Location")
    latitude = fields.Char("Latitude")
    longitude = fields.Char("Longitude")
    distance = fields.Float(
        "Distance From Location",
        compute="_compute_distance",
        search="_search_distance",
        compute_sudo=False,
        help="The current location can be set in your preferences (from the top right menu)",
    )
    active = fields.Boolean(default=True)
    artist_id = fields.Many2one("oomusic.artist", "Artist", ondelete="cascade", index=True)
    user_id = fields.Many2one(
        "res.users", related="artist_id.user_id", store=True, index=True, related_sudo=False
    )
    bit_follow = fields.Selection(related="artist_id.bit_follow", related_sudo=False)

    def name_get(self):
        return [(r.id, "{}, {} ({})".format(r.artist_id.name, r.country, r.city)) for r in self]

    def _compute_distance(self):
        def haversine(p1, p2):
            # Mean earth radius - https://en.wikipedia.org/wiki/Earth_radius#Mean_radius
            AVG_EARTH_RADIUS_KM = 6371.0088

            # Convert latitudes/longitudes from decimal degrees to radians
            lat1, lng1, lat2, lng2 = map(radians, (p1[0], p1[1], p2[0], p2[1]))

            # Compute haversine
            lat = lat2 - lat1
            lng = lng2 - lng1
            d = sin(lat * 0.5) ** 2 + cos(lat1) * cos(lat2) * sin(lng * 0.5) ** 2
            return 2 * AVG_EARTH_RADIUS_KM * asin(sqrt(d))

        loc_user = (self.env.user.latitude, self.env.user.longitude)
        for event in self.filtered(lambda r: r.latitude and r.longitude):
            loc_event = (float(event.latitude), float(event.longitude))
            event.distance = haversine(loc_user, loc_event)

    def _search_distance(self, operator, value):
        if operator not in SYMBOL_NAME_MAP:
            return [("id", "in", self.search([]).ids)]
        event_ids = [
            event["id"]
            for event in self.search([]).read(["id", "distance"])
            if getattr(op, SYMBOL_NAME_MAP[operator])(event["distance"], value)
        ]
        return [("id", "in", event_ids)]

    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        event_ids = super(MusicBandsintownEvent, self)._search(
            args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )
        if self.env.user.max_distance:
            event_ids = [
                event["id"]
                for event in self.browse(event_ids).read(["id", "distance"])
                if event["distance"] <= self.env.user.max_distance
            ]
        return event_ids

    def _create_from_cache(self, cache):
        self.env.cr.execute("SELECT name from oomusic_bandsintown_event")
        res = self.env.cr.fetchall()
        bit_ids = {r[0] for r in res}
        to_create = []
        for artist in cache:
            events = json.loads(cache[artist] or "{}")
            for event in events:
                if event["id"] not in bit_ids:
                    to_create.append(
                        {
                            "name": event["id"],
                            "date_event": event["datetime"][:10],
                            "country": event["venue"].get("country"),
                            "region": event["venue"].get("region"),
                            "city": event["venue"].get("city"),
                            "location": event["venue"].get("name"),
                            "latitude": event["venue"].get("latitude"),
                            "longitude": event["venue"].get("longitude"),
                            "artist_id": artist[0],
                        }
                    )
        self.create(to_create)
