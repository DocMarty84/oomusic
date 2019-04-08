# -*- coding: utf-8 -*-

import json

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class MusicAlbum(models.Model):
    _name = "oomusic.album"
    _description = "Music Album"
    _order = "year desc, name"
    _inherit = ["oomusic.download.mixin", "oomusic.preference.mixin"]

    create_date = fields.Datetime(index=True)

    name = fields.Char("Album", index=True)
    track_ids = fields.One2many("oomusic.track", "album_id", "Tracks", readonly=True)
    artist_id = fields.Many2one("oomusic.artist", "Artist")
    genre_id = fields.Many2one("oomusic.genre", "Genre")
    year = fields.Char("Year", index=True)
    folder_id = fields.Many2one("oomusic.folder", "Folder", index=True, required=True)
    user_id = fields.Many2one(
        "res.users",
        string="User",
        index=True,
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.user,
    )
    in_playlist = fields.Boolean("In Current Playlist", compute="_compute_in_playlist")

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
    tag_ids = fields.Many2many(
        "oomusic.tag",
        string="Custom Tags",
        compute="_compute_tag_ids",
        inverse="_inverse_tag_ids",
        search="_search_tag_ids",
    )

    image_folder = fields.Binary(
        "Folder Image", related="folder_id.image_folder", related_sudo=False
    )
    image_big = fields.Binary("Big-sized Image", related="folder_id.image_big", related_sudo=False)
    image_medium = fields.Binary(
        "Medium-sized Image", related="folder_id.image_medium", related_sudo=False
    )
    image_medium_cache = fields.Binary(
        "Cache Of Medium-sized Image", related="folder_id.image_medium_cache", related_sudo=False
    )
    image_small = fields.Binary(
        "Small-sized Image", related="folder_id.image_small", related_sudo=False
    )

    def _compute_in_playlist(self):
        playlist = self.env["oomusic.playlist"].search([("current", "=", True)], limit=1)
        if not playlist:
            return
        query = """
            SELECT album_id
            FROM oomusic_track
            WHERE id IN (
                SELECT track_id
                FROM oomusic_playlist_line
                WHERE playlist_id = %s
            )
        """
        self.env.cr.execute(query, (playlist.id,))
        album_ids_in_playlist = list({r[0] for r in self.env.cr.fetchall() if r[0]})
        for album in self & self.env["oomusic.album"].browse(album_ids_in_playlist):
            if all([t.in_playlist for t in album.track_ids]):
                album.in_playlist = True

    @api.multi
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

    def _lastfm_album_getinfo(self):
        self.ensure_one()
        url = (
            "https://ws.audioscrobbler.com/2.0/?method=album.getinfo&artist="
            + self.artist_id.name
            + "&album="
            + self.name
        )
        return json.loads(self.env["oomusic.lastfm"].get_query(url))
