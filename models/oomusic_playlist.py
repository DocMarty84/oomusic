# -*- coding: utf-8 -*-

import json
import random

from odoo import fields, models, api
from odoo.exceptions import MissingError

class MusicPlaylist(models.Model):
    _name = 'oomusic.playlist'
    _description = 'Music Playlist'

    def _default_current(self):
        return not bool(self.env['oomusic.playlist'].search([('current', '=', True)]))

    name = fields.Char('Name', required="1")
    user_id = fields.Many2one(
        'res.users', string='User', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.user
    )
    comment = fields.Char('Comment')
    current = fields.Boolean('Current', default=lambda self: self._default_current())
    public = fields.Boolean('Shared', default=False)
    playlist_line_ids = fields.One2many('oomusic.playlist.line', 'playlist_id', string='Tracks')

    album_id = fields.Many2one(
        'oomusic.album', string='Add Album Tracks', store=False,
        help='Encoding help. When selected, the associated album tracks are added to the playlist.')

    artist_id = fields.Many2one(
        'oomusic.artist', string='Add Artist Tracks', store=False,
        help='Encoding help. When selected, the associated artist tracks are added to the playlist.')

    def _add_tracks(self, tracks, onchange=False):
        # Set starting sequence
        seq = self.playlist_line_ids[-1:].sequence or 10

        PlaylistLine = self.env['oomusic.playlist.line']
        playlist_tracks_ids = set(self.playlist_line_ids.mapped('track_id').ids)
        for track in tracks:
            if track.id in playlist_tracks_ids:
                continue
            playlist_tracks_ids.add(track.id)
            seq = seq + 1
            data = {
                'sequence': seq,
                'track_id': track.id,
            }
            if onchange:
                # This will keep the line displayed in a (more or less) correct order while they
                # are added
                PlaylistLine |= PlaylistLine.new(data)
            else:
                data['playlist_id'] = self.id
                PlaylistLine.create(data)

        if onchange:
            self.playlist_line_ids += PlaylistLine

    @api.onchange('album_id')
    def _onhange_album_id(self):
        self._add_tracks(self.album_id.track_ids, onchange=True)
        self.album_id = False
        return {}

    @api.onchange('artist_id')
    def _onhange_artist_id(self, onchange=True):
        self._add_tracks(self.artist_id.track_ids, onchange=True)
        self.artist_id = False
        return {}

    @api.multi
    def action_purge(self):
        for playlist in self:
            playlist.playlist_line_ids.unlink()

    @api.multi
    def action_current(self):
        self.ensure_one()
        self.env['oomusic.playlist'].search([]).write({'current': False})
        self.current = True


class MusicPlaylistLine(models.Model):
    _name = 'oomusic.playlist.line'
    _description = 'Music Playlist Track'
    _order = 'sequence'

    sequence = fields.Integer('Sequence', default=10)
    playlist_id = fields.Many2one('oomusic.playlist', 'Playlist', required=True, ondelete='cascade')
    playing = fields.Boolean('Playing', default=False)
    track_id = fields.Many2one('oomusic.track', 'Track', required=True, ondelete='cascade')
    track_number = fields.Char(
        'Track #', related='track_id.track_number', readonly=True)
    album_id = fields.Many2one(
        'oomusic.album', 'Album', related='track_id.album_id', readonly=True)
    artist_id = fields.Many2one(
        'oomusic.artist', 'Artist', related='track_id.artist_id', readonly=True)
    genre_id = fields.Many2one(
        'oomusic.genre', 'Genre', related='track_id.genre_id', readonly=True)
    year = fields.Char('Year', related='track_id.year', readonly=True)
    duration = fields.Integer('Duration', related='track_id.duration', readonly=True)
    duration_min = fields.Float('Duration', related='track_id.duration_min', readonly=True)
    user_id = fields.Many2one('res.users', related='playlist_id.user_id', store=True, index=True)
    dummy_field = fields.Boolean('Dummy field')

    @api.multi
    def oomusic_play(self, seek=0):
        # Update playing status and stats
        self.playlist_id.playlist_line_ids.write({'playing': False})
        self.write({'playing': True})
        self.track_id.write({
            'last_play': fields.Datetime.now(),
            'play_count': self.track_id.play_count + 1,
        })

        res = {}
        res['playlist_line_id'] = self.id
        res.update(self.track_id._oomusic_info(seek=seek))
        return json.dumps(res)

    @api.multi
    def oomusic_previous(self, shuffle=False):
        res = {}
        # User might have removed the line from the playlist in the meantime
        try:
            lines = self.playlist_id.playlist_line_ids
        except MissingError:
            return json.dumps(res)
        if shuffle:
            return self.oomusic_shuffle()
        for i in xrange(0, len(lines)):
            if lines[i].id == self.id:
                if i > 0:
                    return lines[i-1].oomusic_play()
                else:
                    return lines[len(lines)-1].oomusic_play()
        return json.dumps(res)

    @api.multi
    def oomusic_next(self, shuffle=False):
        res = {}
        # User might have removed the line from the playlist in the meantime
        try:
            lines = self.playlist_id.playlist_line_ids
        except MissingError:
            return json.dumps(res)
        if shuffle:
            return self.oomusic_shuffle()
        for i in xrange(0, len(lines)):
            if lines[i].id == self.id:
                if i < (len(lines) - 1):
                    return lines[i+1].oomusic_play()
                else:
                    return lines[0].oomusic_play()
        return json.dumps(res)

    @api.multi
    def oomusic_star(self):
        try:
            self.track_id.write({'star': '1'})
        except MissingError:
            return
        return

    def oomusic_shuffle(self):
        lines = self.playlist_id.playlist_line_ids
        return lines[random.randint(0, len(lines)-1)].oomusic_play()

    def oomusic_last_track(self):
        Playlist = self.env['oomusic.playlist'].search([('current', '=', True)], limit=1)
        if Playlist and Playlist.playlist_line_ids:
            PlaylistLine = Playlist.playlist_line_ids.filtered(lambda r: r.playing is True)
            if not PlaylistLine:
                PlaylistLine = Playlist.playlist_line_ids
            return PlaylistLine[0].oomusic_play()
        else:
            return json.dumps({})
