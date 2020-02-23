# -*- coding: utf-8 -*-

from odoo import fields, models


class MusicSuggestion(models.TransientModel):
    _name = "oomusic.suggestion"
    _description = "Music Suggestion page"

    name_tracks = fields.Char("Name Tracks", default="Tracks")
    name_albums = fields.Char("Name Albums", default="Albums")

    track_last_played = fields.Many2many(
        "oomusic.track",
        string="Last Played",
        store=False,
        readonly=True,
        default=lambda s: s._default_track_last_played(),
    )
    track_recently_added = fields.Many2many(
        "oomusic.track",
        string="Recently Added Tracks",
        store=False,
        default=lambda s: s._default_track_recently_added(),
    )
    track_random = fields.Many2many(
        "oomusic.track",
        string="Random Tracks",
        store=False,
        readonly=True,
        default=lambda s: s._default_track_random(),
    )

    album_recently_added = fields.Many2many(
        "oomusic.album",
        string="Recently Added Albums",
        store=False,
        readonly=True,
        default=lambda s: s._default_album_recently_added(),
    )
    album_random = fields.Many2many(
        "oomusic.album",
        string="Random Albums",
        store=False,
        readonly=True,
        default=lambda s: s._default_album_random(),
    )

    def _default_track_last_played(self):
        return [
            p["res_id"]
            for p in self.env["oomusic.preference"].search_read(
                fields=["res_id"],
                domain=[("play_count", ">", 0), ("res_model", "=", "oomusic.track")],
                order="last_play desc",
                limit=10,
            )
        ]

    def _default_track_recently_added(self):
        return [
            p["id"]
            for p in self.env["oomusic.track"].search_read(
                fields=["id"], domain=[], order="id desc", limit=10,
            )
        ]

    def _default_track_random(self):
        folder_sharing = (
            "inactive" if self.env.ref("oomusic.oomusic_track").sudo().perm_read else "active"
        )
        query = "SELECT id FROM oomusic_track "
        if folder_sharing == "inactive":
            query += "WHERE user_id = {} ".format(self.env.uid)
        query += "ORDER BY RANDOM() "
        query += "LIMIT 10"
        self.env.cr.execute(query)
        res = self.env.cr.fetchall()

        return [r[0] for r in res]

    def _default_album_recently_added(self):
        return [
            p["id"]
            for p in self.env["oomusic.album"].search_read(
                fields=["id"], domain=[], order="id desc", limit=10,
            )
        ]

    def _default_album_random(self):
        folder_sharing = (
            "inactive" if self.env.ref("oomusic.oomusic_track").sudo().perm_read else "active"
        )
        query = "SELECT id FROM oomusic_album "
        if folder_sharing == "inactive":
            query += "WHERE user_id = {} ".format(self.env.uid)
        query += "ORDER BY RANDOM() "
        query += "LIMIT 15"
        self.env.cr.execute(query)
        res = self.env.cr.fetchall()

        return [r[0] for r in res]
