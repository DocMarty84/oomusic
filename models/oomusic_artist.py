# -*- coding: utf-8 -*-

import base64
import json
import logging
from pprint import pformat
from psycopg2 import OperationalError
from random import sample
import urllib.request

from odoo import fields, models, api, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MusicArtist(models.Model):
    _name = "oomusic.artist"
    _description = "Music Artist"
    _order = "name"
    _inherit = ["oomusic.download.mixin", "oomusic.preference.mixin"]

    name = fields.Char("Artist", index=True)
    track_ids = fields.One2many("oomusic.track", "artist_id", string="Tracks", readonly=True)
    album_ids = fields.One2many("oomusic.album", "artist_id", string="Albums", readonly=True)
    user_id = fields.Many2one(
        "res.users",
        string="User",
        index=True,
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.user,
    )

    star = fields.Selection(
        [("0", "Normal"), ("1", "I Like It!")],
        "Favorite",
        compute="_compute_star",
        inverse="_inverse_star",
        search="_search_star",
    )
    rating = fields.Selection(
        [("0", "0"), ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5")],
        "Rating",
        compute="_compute_rating",
        inverse="_inverse_rating",
        search="_search_rating",
    )

    fm_image = fields.Binary(
        "Image", compute="_compute_fm_image", help="Image of the artist, obtained thanks to LastFM."
    )
    fm_image_cache = fields.Binary(
        "Cache Of Image", attachment=True, help="Image of the artist, obtained thanks to LastFM."
    )
    sp_image = fields.Binary(
        "Spotify Image",
        compute="_compute_sp_image",
        help="Image of the artist, obtained thanks to Spotify.",
    )
    sp_image_cache = fields.Binary(
        "Cache Of Spotify Image",
        attachment=True,
        help="Image of the artist, obtained thanks to Spotify.",
    )
    fm_getinfo_bio = fields.Char("Biography", compute="_compute_fm_getinfo")
    fm_gettoptracks_track_ids = fields.Many2many(
        "oomusic.track", string="Top Tracks", compute="_compute_fm_gettoptracks"
    )
    fm_getsimilar_artist_ids = fields.Many2many(
        "oomusic.artist", string="Similar Artists", compute="_compute_fm_getsimilar"
    )
    bit_follow = fields.Selection(
        [("normal", "Not Followed"), ("done", "Followed")],
        "Follow Events",
        compute="_compute_bit_follow",
        inverse="_inverse_bit_follow",
        search="_search_bit_follow",
    )
    bit_event_ids = fields.One2many(
        "oomusic.bandsintown.event", "artist_id", string="Events", readonly=True
    )
    tag_ids = fields.Many2many(
        "oomusic.tag",
        string="Custom Tags",
        compute="_compute_tag_ids",
        inverse="_inverse_tag_ids",
        search="_search_tag_ids",
    )

    _sql_constraints = [
        ("oomusic_artist_name_uniq", "unique(name, user_id)", "Artist name must be unique!")
    ]

    @api.depends("name")
    def _compute_fm_image(self):
        for artist in self:
            if artist.fm_image_cache and not self.env.context.get("build_cache"):
                artist.fm_image = artist.fm_image_cache
                continue

            resized_images = {"image_medium": False}
            req_json = artist._lastfm_artist_getinfo()
            try:
                _logger.debug("Retrieving image for artist %s...", artist.name)
                for image in req_json["artist"]["image"]:
                    if image["size"] == "large" and image["#text"]:
                        image_content = urllib.request.urlopen(image["#text"], timeout=5).read()
                        resized_images = tools.image_get_resized_images(
                            base64.b64encode(image_content),
                            return_big=False,
                            return_medium=True,
                            return_small=False,
                        )
                        break
            except KeyError:
                _logger.warning(
                    'No image found for artist "%s" (id: %s). json contains:\n%s',
                    artist.name,
                    artist.id,
                    pformat(req_json),
                    exc_info=True,
                )
            except urllib.error.HTTPError:
                _logger.warning(
                    'HTTPError when retrieving image for artist "%s" (id: %s). '
                    "Forcing LastFM info refresh.",
                    artist.name,
                    artist.id,
                    exc_info=True,
                )
                artist._lastfm_artist_getinfo(force=True)

            # Avoid useless save in cache
            if resized_images["image_medium"] == artist.fm_image_cache:
                continue

            artist.fm_image = resized_images["image_medium"]

            # Save in cache
            try:
                artist.sudo().write({"fm_image_cache": resized_images["image_medium"]})
                self.env.cr.commit()
            except OperationalError:
                _logger.warning(
                    "Error when writing image cache for artist id: %s", artist.id, exc_info=True
                )

    @api.depends("name")
    def _compute_sp_image(self):
        build_cache = self.env.context.get("build_cache", False)
        force = self.env.context.get("force", False)
        for artist in self:
            if artist.sp_image_cache and not build_cache and not force:
                artist.sp_image = artist.sp_image_cache
                continue

            resized_images = {"image_medium": False}
            req_json = artist._spotify_artist_search(force=force)
            try:
                _logger.debug("Retrieving image for artist %s...", artist.name)
                item = req_json["artists"]["items"][0] if req_json["artists"]["items"] else {}
                images = item.get("images")
                if not images:
                    _logger.info('No image found for artist "%s" (id: %s)', artist.name, artist.id)
                    continue
                for image in images:
                    image_content = urllib.request.urlopen(image["url"], timeout=5).read()
                    resized_images = tools.image_get_resized_images(
                        base64.b64encode(image_content),
                        return_big=False,
                        return_medium=True,
                        return_small=False,
                    )
                    break
            except KeyError:
                _logger.warning(
                    "No image found for artist '%s' (id: %s). json contains:\n%s",
                    artist.name,
                    artist.id,
                    pformat(req_json),
                    exc_info=True,
                )
            except urllib.error.HTTPError:
                _logger.warning(
                    "HTTPError when retrieving image for artist '%s' (id: %s). "
                    "Forcing Spotify info refresh.",
                    artist.name,
                    artist.id,
                    exc_info=True,
                )
                artist._spotify_artist_search(force=True)

            # Avoid useless save in cache
            if resized_images["image_medium"] == artist.sp_image_cache:
                continue

            artist.sp_image = resized_images["image_medium"]

            # Save in cache
            try:
                artist.sudo().write({"sp_image_cache": resized_images["image_medium"]})
                self.env.cr.commit()
            except OperationalError:
                _logger.warning(
                    "Error when writing image cache for artist id: %s", artist.id, exc_info=True
                )

    def _compute_fm_getinfo(self):
        for artist in self:
            req_json = artist._lastfm_artist_getinfo()
            try:
                artist.fm_getinfo_bio = req_json["artist"]["bio"]["summary"].replace("\n", "<br/>")
            except KeyError:
                artist.fm_getinfo_bio = _("Biography not found")
                _logger.warning(
                    "Biography not found for artist '%s' (id: %s). json contains:\n%s",
                    artist.name,
                    artist.id,
                    pformat(req_json),
                    exc_info=True,
                )

    def _compute_fm_gettoptracks(self):
        # Create a global cache dict for all artists to avoid multiple search calls.
        tracks = self.env["oomusic.track"].search_read(
            [("artist_id", "in", self.ids)], ["id", "name", "artist_id"]
        )
        tracks = {(t["artist_id"][0], t["name"].lower()): t["id"] for t in tracks}

        for artist in self:
            req_json = artist._lastfm_artist_gettoptracks()
            try:
                t_tracks = [
                    tracks[(artist.id, t["name"].lower())]
                    for t in req_json["toptracks"]["track"]
                    if (artist.id, t["name"].lower()) in tracks
                ]
                artist.fm_gettoptracks_track_ids = t_tracks[:10]
            except KeyError:
                _logger.warning(
                    "Top tracks not found for artist '%s' (id: %s). json contains:\n%s",
                    artist.name,
                    artist.id,
                    pformat(req_json),
                    exc_info=True,
                )

    def _compute_fm_getsimilar(self):
        for artist in self:
            req_json = artist._lastfm_artist_getsimilar()
            try:
                s_artists = self.env["oomusic.artist"]
                for s_artist in req_json["similarartists"]["artist"]:
                    s_artists |= self.env["oomusic.artist"].search(
                        [("name", "=ilike", s_artist["name"])], limit=1
                    )
                    if len(s_artists) > 4:
                        break
                artist.fm_getsimilar_artist_ids = s_artists.ids
            except KeyError:
                _logger.warning(
                    "Similar artists not found for artist '%s' (id: %s). json contains:\n%s",
                    artist.name,
                    artist.id,
                    pformat(req_json),
                    exc_info=True,
                )

    def action_add_to_playlist(self):
        playlist = self.env["oomusic.playlist"].search([("current", "=", True)], limit=1)
        if not playlist:
            raise UserError(_("No current playlist found!"))
        if self.env.context.get("purge"):
            playlist.action_purge()
        lines = playlist._add_tracks(self.mapped("track_ids"))
        if self.env.context.get("play") and lines:
            return {
                "type": "ir.actions.act_play",
                "res_model": "oomusic.playlist.line",
                "res_id": lines[0].id,
            }

    def action_reload_artist_info(self):
        for artist in self:
            artist._lastfm_artist_getinfo(force=True)
            artist._lastfm_artist_getsimilar(force=True)
            artist._lastfm_artist_gettoptracks(force=True)
            artist.with_context(force=True)._compute_sp_image()

    def action_reload_bit_info(self):
        for artist in self:
            artist._bandsintown_artist_getevents(force=True)

    @api.model
    def cron_build_image_cache(self):
        # Build a random sample of 500 artists to compute the images for. Every 50, the cache is
        # flushed.
        size_sample = 500
        size_step = 50
        artists = self.search([]).with_context(prefetch_fields=False)
        artists_sample = sample(artists.ids, min(size_sample, len(artists)))
        artists = self.browse(artists_sample).with_context(build_cache=True, prefetch_fields=False)
        for i in range(0, len(artists), size_step):
            artist = artists[i : i + size_step]
            artist._compute_sp_image()
            self.invalidate_cache()

    def _lastfm_artist_getinfo(self, force=False):
        self.ensure_one()
        url = "https://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist=" + self.name
        return json.loads(self.env["oomusic.lastfm"].get_query(url, force=force))

    def _lastfm_artist_getsimilar(self, force=False):
        self.ensure_one()
        url = "https://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&artist=" + self.name
        return json.loads(self.env["oomusic.lastfm"].get_query(url, force=force))

    def _lastfm_artist_gettoptracks(self, force=False):
        self.ensure_one()
        url = "https://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&artist=" + self.name
        return json.loads(self.env["oomusic.lastfm"].get_query(url, force=force))

    def _bandsintown_artist_getevents(self, force=False):
        self.ensure_one()
        url = "https://rest.bandsintown.com/artists/{}/events".format(self.name)
        cache = {}
        cache[(self.id, self.name)] = self.env["oomusic.bandsintown"].get_query(url, force=force)
        self.env["oomusic.bandsintown.event"].sudo()._create_from_cache(cache)

    def _spotify_artist_search(self, force=False):
        self.ensure_one()
        url = "https://api.spotify.com/v1/search?type=artist&limit=1&q=" + self.name
        return json.loads(self.env["oomusic.spotify"].get_query(url, force=force))
