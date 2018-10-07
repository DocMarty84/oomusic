# -*- coding: utf-8 -*-

import random

from odoo import fields, models, api


class MusicSuggestion(models.TransientModel):
    _name = 'oomusic.suggestion'
    _description = 'Music Suggestion page'

    name_tracks = fields.Char('Name Tracks', default='Tracks')
    name_albums = fields.Char('Name Albums', default='Albums')

    track_last_played = fields.Many2many(
        'oomusic.track', string='Last Played', compute='_compute_track_last_played')
    track_recently_added = fields.Many2many(
        'oomusic.track', string='Recently Added Tracks', compute='_compute_track_recently_added')
    track_random = fields.Many2many(
        'oomusic.track', string='Random Tracks', compute='_compute_track_random')

    album_recently_added = fields.Many2many(
        'oomusic.album', string='Recently Added Albums', compute='_compute_album_recently_added')
    album_random = fields.Many2many(
        'oomusic.album', string='Random Albums', compute='_compute_album_random')

    @api.depends('name_tracks')
    def _compute_track_last_played(self):
        self.track_last_played = self.env['oomusic.preference'].search(
            [('play_count', '>', 0), ('res_model', '=', 'oomusic.track')],
            order='last_play desc', limit=10).mapped('res_id')

    @api.depends('name_tracks')
    def _compute_track_recently_added(self):
        self.track_recently_added = self.env['oomusic.track'].search(
            [], order='id desc', limit=10)

    @api.depends('name_tracks')
    def _compute_track_random(self):
        folder_sharing = (
            'inactive' if self.env.ref('oomusic.oomusic_track').sudo().perm_read else 'active'
        )
        query = 'SELECT id FROM oomusic_track '
        if folder_sharing == 'inactive':
            query += 'WHERE user_id = {}'.format(self.env.uid)
        self.env.cr.execute(query)
        res = self.env.cr.fetchall()
        if not res:
            return

        self.track_random = random.sample([r[0] for r in res], min(10, len(res)))

    @api.depends('name_albums')
    def _compute_album_recently_added(self):
        self.album_recently_added = self.env['oomusic.album'].search(
            [], order='id desc', limit=10)

    @api.depends('name_albums')
    def _compute_album_random(self):
        folder_sharing = (
            'inactive' if self.env.ref('oomusic.oomusic_track').sudo().perm_read else 'active'
        )
        query = 'SELECT id FROM oomusic_album '
        if folder_sharing == 'inactive':
            query += 'WHERE user_id = {}'.format(self.env.uid)
        self.env.cr.execute(query)
        res = self.env.cr.fetchall()
        if not res:
            return

        self.album_random = random.sample([r[0] for r in res], min(15, len(res)))
