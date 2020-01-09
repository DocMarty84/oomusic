# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MusicSuggestion(models.TransientModel):
    _name = "oomusic.suggestion"
    _description = "Music Suggestion page"

    name_tracks = fields.Char("Name Tracks", default="Tracks")
    name_albums = fields.Char("Name Albums", default="Albums")

    track_last_played = fields.Many2many(
        "oomusic.track", string="Last Played", compute="_compute_track_last_played"
    )
    track_recently_added = fields.Many2many(
        "oomusic.track", string="Recently Added Tracks", compute="_compute_track_recently_added"
    )
    track_random = fields.Many2many(
        "oomusic.track", string="Random Tracks", compute="_compute_track_random"
    )

    album_recently_added = fields.Many2many(
        "oomusic.album", string="Recently Added Albums", compute="_compute_album_recently_added"
    )
    album_random = fields.Many2many(
        "oomusic.album", string="Random Albums", compute="_compute_album_random"
    )

    @api.depends("name_tracks")
    def _compute_track_last_played(self):
        self.track_last_played = [
            p["res_id"]
            for p in self.env["oomusic.preference"]
            .search(
                [("play_count", ">", 0), ("res_model", "=", "oomusic.track")],
                order="last_play desc",
                limit=10,
            )
            .read(["res_id"])
        ]

    @api.depends("name_tracks")
    def _compute_track_recently_added(self):
        self.track_recently_added = self.env["oomusic.track"].search([], order="id desc", limit=10)

    @api.depends("name_tracks")
    def _compute_track_random(self):
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

        self.track_random = [r[0] for r in res]

    @api.depends("name_albums")
    def _compute_album_recently_added(self):
        self.album_recently_added = self.env["oomusic.album"].search([], order="id desc", limit=10)

    @api.depends("name_albums")
    def _compute_album_random(self):
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

        self.album_random = [r[0] for r in res]
