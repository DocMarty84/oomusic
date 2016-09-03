# -*- coding: utf-8 -*-

import random

from odoo import fields, models, api

class MusicSuggestion(models.TransientModel):
    _name = 'oomusic.suggestion'
    _description = 'Music Suggestion page'

    name_tracks = fields.Char('Name', default='Tracks')
    name_albums = fields.Char('Name', default='Albums')

    track_last_played = fields.Many2many(
        'oomusic.track', string='Last Played', compute='_compute_track_last_played')
    track_recently_added = fields.Many2many(
        'oomusic.track', string='Recently Added', compute='_compute_track_recently_added')
    track_random = fields.Many2many(
        'oomusic.track', string='Random', compute='_compute_track_random')

    album_recently_added = fields.Many2many(
        'oomusic.album', string='Recently Added', compute='_compute_album_recently_added')
    album_random = fields.Many2many(
        'oomusic.album', string='Random', compute='_compute_album_random')

    @api.depends('name_tracks')
    def _compute_track_last_played(self):
        Track = self.env['oomusic.track'].search(
            [('play_count', '>', 0)], order='last_play desc', limit=10)
        self.track_last_played = Track.ids

    @api.depends('name_tracks')
    def _compute_track_recently_added(self):
        Track = self.env['oomusic.track'].search([], order='create_date desc', limit=10)
        self.track_recently_added = Track.ids

    @api.depends('name_tracks')
    def _compute_track_random(self):
        params = (self.env.user.id, )
        query = "SELECT id FROM oomusic_track WHERE user_id = %s;"
        self.env.cr.execute(query, params)
        res = self.env.cr.fetchall()
        if not res:
            return

        random_track_ids = random.sample([r[0] for r in res], min(10, len(res)))
        Track = self.env['oomusic.track'].browse(random_track_ids)
        self.track_random = Track.ids

    @api.depends('name_albums')
    def _compute_album_recently_added(self):
        Album = self.env['oomusic.album'].search([], order='create_date desc', limit=10)
        self.album_recently_added = Album.ids

    @api.depends('name_albums')
    def _compute_album_random(self):
        params = (self.env.user.id, )
        query = "SELECT id FROM oomusic_album WHERE user_id = %s;"
        self.env.cr.execute(query, params)
        res = self.env.cr.fetchall()
        if not res:
            return

        random_album_ids = random.sample([r[0] for r in res], min(15, len(res)))
        Album = self.env['oomusic.album'].browse(random_album_ids)
        self.album_random = Album.ids
