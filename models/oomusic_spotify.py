# -*- coding: utf-8 -*-

import base64
import datetime
import hashlib
import json
import logging
import time
from pprint import pformat
from random import sample

import requests
from werkzeug.urls import url_fix

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MusicSpotify(models.Model):
    _name = "oomusic.spotify"
    _description = "Spotify Cache Management"

    name = fields.Char("URL Hash", index=True, required=True)
    url = fields.Char("URL", required=True)
    content = fields.Char("Result", required=True)
    expiry_date = fields.Datetime("Expiry Date", required=True)
    removal_date = fields.Datetime("Removal Date", required=True)

    _sql_constraints = [("oomusic_spotify_name_uniq", "unique(name)", "URL hash must be unique!")]

    def get_query(self, url, sleep=0.0, force=False):
        ConfigParam = self.env["ir.config_parameter"].sudo()
        sp_cache = int(ConfigParam.get_param("oomusic.spotify_cache", 182))
        ext_info = ConfigParam.get_param("oomusic.ext_info", "auto")

        url = url_fix(url).encode("utf-8")
        url_hash = hashlib.sha1(url).hexdigest()

        Spotify = self.search([("name", "=", url_hash)])
        if force or not Spotify or Spotify.expiry_date < fields.Datetime.now():
            content = "{}"
            if ext_info == "manual" and not force:
                content = Spotify.content or content
                return content
            try:
                time.sleep(sleep)
                headers = {
                    "Authorization": "Bearer {}".format(
                        self.env["oomusic.spotify.token"]._get_token()
                    )
                }
                r = requests.get(url, headers=headers, timeout=3.0)
                if r.status_code == 200:
                    content = r.content.decode("utf-8")
                else:
                    _logger.warning(
                        "Error getting Spotify info.\nError code: %s\nURL: %s\nheaders: %s",
                        r.status_code,
                        url,
                        pformat(headers),
                    )
                    return content
            except:
                _logger.warning(
                    "Error getting Spotify info.\nError code: %s\nURL: %s\nheaders: %s",
                    r.status_code,
                    url,
                    pformat(headers),
                    exc_info=True,
                )
                return content

            expiry_date = datetime.datetime.utcnow() + datetime.timedelta(days=sp_cache)
            removal_date = datetime.datetime.utcnow() + datetime.timedelta(days=sp_cache + 14)

            # Save in cache
            if not Spotify:
                writer = self.create
            else:
                writer = Spotify.write
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
            content = Spotify.content or "{}"

        return content

    @api.model
    def cron_build_spotify_cache(self):
        # Build cache for artists. Limit to 200 artists chosen randomly to avoid running for
        # unexpectedly long periods of time.
        self.env.cr.execute("SELECT name from oomusic_artist")
        res = self.env.cr.fetchall()
        artists = {r[0] for r in res}
        for artist in sample(artists, min(200, len(artists))):
            _logger.debug('Gettting Spotify cache for artist "%s"...', artist)
            url = "https://api.spotify.com/v1/search?type=artist&limit=1&q=" + artist
            self.get_query(url, sleep=0.25)

        # Clean-up outdated entries
        self.search([("removal_date", "<", fields.Datetime.now())]).unlink()
        self.env["oomusic.spotify.token"].search(
            [("expiry_date", "<", fields.Datetime.now())]
        ).unlink()


class MusicSpotifyToken(models.Model):
    _name = "oomusic.spotify.token"
    _description = "Spotify Token"

    name = fields.Char("Token", required=True)
    expiry_date = fields.Datetime("Expiry Date", required=True, index=True)
    token_type = fields.Char("Type")
    scope = fields.Char("Scope")

    @api.model
    def _get_auth(self):
        ConfigParam = self.env["ir.config_parameter"].sudo()
        sp_id = ConfigParam.get_param("oomusic.spotify_id")
        sp_secret = ConfigParam.get_param("oomusic.spotify_secret")
        if not sp_id or not sp_secret:
            return ""
        return base64.b64encode(sp_id.encode("utf-8") + b":" + sp_secret.encode("utf-8")).decode()

    @api.model
    def _get_token(self):
        now = datetime.datetime.now()
        # Find existing token...
        token = self.search([("expiry_date", ">", now)], limit=1)
        if token:
            return token.name

        # ... or create a new one.
        url = "https://accounts.spotify.com/api/token"
        data = {"grant_type": "client_credentials"}
        headers = {"Authorization": "Basic {}".format(self._get_auth())}
        res = requests.post(url, data=data, headers=headers)
        if res.status_code != 200:
            _logger.warning(
                "Error getting Spotify token.\nError code: %s\nURL: %s\ndata: %s\nheaders: %s",
                res.status_code,
                url,
                pformat(data),
                headers,
            )
            return ""
        content = json.loads(res.content.decode("utf-8"))
        self.create(
            {
                "name": content["access_token"],
                "expiry_date": now + datetime.timedelta(seconds=content["expires_in"] - 120),
                "token_type": content.get("token_type"),
                "scope": content.get("scope"),
            }
        )
        self.env.cr.commit()
        return content["access_token"]
