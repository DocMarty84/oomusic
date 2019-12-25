# -*- coding: utf-8 -*-

import datetime
import hashlib
import logging
import time

import requests
from werkzeug.urls import url_fix

from odoo import models, api, fields

_logger = logging.getLogger(__name__)


class MusicLastfm(models.Model):
    _name = "oomusic.lastfm"
    _description = "LastFM Cache Management"

    name = fields.Char("URL Hash", index=True, required=True)
    url = fields.Char("URL", required=True)
    content = fields.Char("Result", required=True)
    expiry_date = fields.Datetime("Expiry Date", required=True)
    removal_date = fields.Datetime("Removal Date", required=True)

    _sql_constraints = [("oomusic_lastfm_name_uniq", "unique(name)", "URL hash must be unique!")]

    def get_query(self, url, sleep=0.0, force=False):
        # Get LastFM key and cache duration
        ConfigParam = self.env["ir.config_parameter"].sudo()
        fm_key = ConfigParam.get_param("oomusic.lastfm_key")
        fm_cache = int(ConfigParam.get_param("oomusic.lastfm_cache", 112))
        ext_info = ConfigParam.get_param("oomusic.ext_info", "auto")
        if not fm_key:
            return "{}"

        url = url_fix(url + "&api_key=" + fm_key + "&format=json").encode("utf-8")
        url_hash = hashlib.sha1(url).hexdigest()

        Lastfm = self.search([("name", "=", url_hash)])
        if force or not Lastfm or Lastfm.expiry_date < fields.Datetime.now():
            content = "{}"
            if ext_info == "manual" and not force:
                content = Lastfm.content or content
                return content
            try:
                time.sleep(sleep)
                r = requests.get(url, timeout=3.0)
                if r.status_code == 200:
                    content = r.content.decode("utf-8")
            except:
                _logger.warning("Error while fetching URL '%s'", url, exc_info=True)

            expiry_date = datetime.datetime.utcnow() + datetime.timedelta(days=fm_cache)
            removal_date = datetime.datetime.utcnow() + datetime.timedelta(days=fm_cache + 14)

            # Save in cache
            if not Lastfm:
                writer = self.create
            else:
                writer = Lastfm.write
            writer(
                {
                    "name": url_hash,
                    "url": url,
                    "content": content,
                    "expiry_date": expiry_date,
                    "removal_date": removal_date,
                }
            )
            self.env.cr.commit()

        else:
            content = Lastfm.content or "{}"

        return content

    @api.model
    def cron_build_lastfm_cache(self):
        # Build cache for artists. Limit to 200 artists chosen randomly to avoid running for
        # unexpectedly long periods of time.
        self.env.cr.execute("SELECT id FROM oomusic_artist ORDER BY RANDOM() LIMIT 200")
        for artist in self.env["oomusic.artist"].browse([r[0] for r in self.env.cr.fetchall()]):
            _logger.debug("Gettting LastFM cache for artist '%s'...", artist.name)
            artist._lastfm_artist_getinfo()
            artist._lastfm_artist_gettoptracks()
            artist._lastfm_artist_getsimilar(sleep=1.0)

        # Clean-up outdated entries
        self.search([("removal_date", "<", fields.Datetime.now())]).unlink()
