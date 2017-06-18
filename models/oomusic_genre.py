# -*- coding: utf-8 -*-

from odoo import fields, models


class MusicGenre(models.Model):
    _name = 'oomusic.genre'
    _description = 'Music Genre'
    _order = 'name'

    name = fields.Char('Music Genre', index=True)
    track_ids = fields.One2many('oomusic.track', 'genre_id', string='Tracks')
    album_ids = fields.One2many('oomusic.album', 'genre_id', string='Albums')
    artist_ids = fields.Many2many('oomusic.artist', string='Artists', compute='_compute_artist_ids')
    user_id = fields.Many2one(
        'res.users', string='User', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.user
    )

    _sql_constraints = [
        ('oomusic_genre_name_uniq', 'unique(name, user_id)', 'Genre name must be unique!'),
    ]

    def _compute_artist_ids(self):
        for genre in self:
            genre.artist_ids = genre.album_ids.mapped('artist_id').sorted(lambda r: r.name)
