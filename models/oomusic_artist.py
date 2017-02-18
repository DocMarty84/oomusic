# -*- coding: utf-8 -*-

import datetime
import json
import time

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT


class MusicArtist(models.Model):
    _name = 'oomusic.artist'
    _description = 'Music Artist'
    _order = 'name'

    name = fields.Char('Artist', index=True)
    track_ids = fields.One2many('oomusic.track', 'artist_id', string='Tracks')
    album_ids = fields.One2many('oomusic.album', 'artist_id', string='Albums')
    user_id = fields.Many2one(
        'res.users', string='User', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.user
    )

    star = fields.Selection(
        [('0', 'Normal'), ('1', 'I Like It!')], 'Favorite', index=True, default='0')
    rating = fields.Selection(
        [('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
        'Rating', default='0',
    )

    fm_getinfo_bio = fields.Char('Biography', compute='_compute_fm_getinfo')
    fm_gettoptracks_track_ids = fields.Many2many(
        'oomusic.track', string='Top Tracks', compute='_compute_fm_gettoptracks')
    fm_getsimilar_artist_ids = fields.Many2many(
        'oomusic.artist', string='Similar Artists', compute='_compute_fm_getsimilar')

    _sql_constraints = [
        ('oomusic_artist_name_uniq', 'unique(name, user_id)', 'Artist name must be unique!'),
    ]

    def _compute_fm_getinfo(self):
        for artist in self:
            url = 'https://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist=' + artist.name
            req_json = json.loads(self.env['oomusic.lastfm'].get_query(url))
            try:
                artist.fm_getinfo_bio = req_json['artist']['bio']['summary'].replace('\n', '<br/>')
            except:
                artist.fm_getinfo_bio = _('Biography not found')

    def _compute_fm_gettoptracks(self):
        for artist in self:
            url = 'https://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&artist=' + artist.name
            req_json = json.loads(self.env['oomusic.lastfm'].get_query(url))
            try:
                t_tracks = self.env['oomusic.track']
                for track in req_json['toptracks']['track']:
                    t_tracks |= self.env['oomusic.track'].search([
                        ('name', '=ilike', track['name']),
                        ('artist_id', '=', artist.id)
                    ], limit=1)
                    if len(t_tracks) > 9:
                        break
                artist.fm_gettoptracks_track_ids = t_tracks.ids
            except:
                pass

    def _compute_fm_getsimilar(self):
        for artist in self:
            url = 'https://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&artist=' + artist.name
            req_json = json.loads(self.env['oomusic.lastfm'].get_query(url))
            try:
                s_artists = self.env['oomusic.artist']
                for s_artist in req_json['similarartists']['artist']:
                    s_artists |= self.env['oomusic.artist'].search([
                        ('name', '=ilike', s_artist['name']),
                    ], limit=1)
                    if len(s_artists) > 4:
                        break
                artist.fm_getsimilar_artist_ids = s_artists.ids
            except:
                pass

    @api.multi
    def action_add_to_playlist(self):
        playlist = self.env['oomusic.playlist'].search([('current', '=', True)], limit=1)
        if not playlist:
            raise UserError(_('No current playlist found!'))
        if self.env.context.get('purge'):
            playlist.action_purge()
        for artist in self:
            playlist._add_tracks(artist.track_ids)
