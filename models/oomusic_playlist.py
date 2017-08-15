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
    norm = fields.Boolean(
        'Normalize', default=False,
        help='Normalize playlist loudness thanks to the EBU R128 normalization. It requires '
             'FFmpeg >=3.2.1 which includes by default the appropriate library (libebur128).\n'
             'Transcoding will be significantly slower when activated, implying larger gaps between'
             ' songs.'
    )
    playlist_line_ids = fields.One2many(
        'oomusic.playlist.line', 'playlist_id', string='Tracks', copy=True)
    album_id = fields.Many2one(
        'oomusic.album', string='Add Album Tracks', store=False,
        help='Encoding help. When selected, the associated album tracks are added to the playlist.')
    artist_id = fields.Many2one(
        'oomusic.artist', string='Add Artist Tracks', store=False,
        help='Encoding help. When selected, the associated artist tracks are added to the playlist.')

    def _add_tracks(self, tracks, onchange=False):
        # Set starting sequence
        seq = self.playlist_line_ids[-1:].sequence or 10

        playlist_line = self.env['oomusic.playlist.line']
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
                playlist_line |= playlist_line.new(data)
            else:
                data['playlist_id'] = self.id
                playlist_line.create(data)

        if onchange:
            self.playlist_line_ids += playlist_line

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
        self.mapped('playlist_line_ids').unlink()

    @api.multi
    def action_current(self):
        self.ensure_one()
        self.env['oomusic.playlist'].search([]).write({'current': False})
        self.current = True

        # Reset 'in_playlist' field. Done with SQL for faster execution.
        self.env.cr.execute('''
            UPDATE oomusic_track SET in_playlist = false
            WHERE user_id = %s
                AND in_playlist = true
            ''', (self.env.uid, ))
        self.env.cr.execute('''
            UPDATE oomusic_album SET in_playlist = false
            WHERE user_id = %s
                AND in_playlist = true
            ''', (self.env.uid, ))

        # Recompute 'in_playlist' field
        self.playlist_line_ids.mapped('track_id').write({'in_playlist': True})


class MusicPlaylistLine(models.Model):
    _name = 'oomusic.playlist.line'
    _description = 'Music Playlist Track'
    _order = 'sequence'

    sequence = fields.Integer('Sequence', default=10)
    playlist_id = fields.Many2one('oomusic.playlist', 'Playlist', required=True, ondelete='cascade')
    playing = fields.Boolean('Playing', default=False)
    track_id = fields.Many2one('oomusic.track', 'Track', required=True, ondelete='cascade')
    track_number = fields.Char(
        'Track #', related='track_id.track_number', readonly=True, related_sudo=False)
    album_id = fields.Many2one(
        'oomusic.album', 'Album', related='track_id.album_id', readonly=True, related_sudo=False)
    artist_id = fields.Many2one(
        'oomusic.artist', 'Artist', related='track_id.artist_id', readonly=True, related_sudo=False)
    genre_id = fields.Many2one(
        'oomusic.genre', 'Genre', related='track_id.genre_id', readonly=True, related_sudo=False)
    year = fields.Char('Year', related='track_id.year', readonly=True, related_sudo=False)
    duration = fields.Integer(
        'Duration', related='track_id.duration', readonly=True, related_sudo=False)
    duration_min = fields.Float(
        'Duration', related='track_id.duration_min', readonly=True, related_sudo=False)
    user_id = fields.Many2one(
        'res.users', related='playlist_id.user_id', store=True, index=True, related_sudo=False)
    dummy_field = fields.Boolean('Dummy field')

    @api.model
    def create(self, vals):
        playlist_line = super(MusicPlaylistLine, self).create(vals)
        if playlist_line.playlist_id.current:
            playlist_line.track_id.write({'in_playlist': True})
        return playlist_line

    @api.multi
    def write(self, vals):
        if 'track_id' in vals:
            self.filtered(lambda r: r.playlist_id.current)\
                .mapped('track_id').write({'in_playlist': False})
        res = super(MusicPlaylistLine, self).write(vals)
        if 'track_id' in vals:
            self.filtered(lambda r: r.playlist_id.current)\
                .mapped('track_id').write({'in_playlist': True})
        return res

    @api.multi
    def unlink(self):
        self.filtered(lambda r: r.playlist_id.current)\
            .mapped('track_id').write({'in_playlist': False})
        return super(MusicPlaylistLine, self).unlink()

    @api.multi
    def oomusic_set_current(self):
        res = {}
        if not self.id:
            return json.dumps(res)

        # Update playing status and stats
        self.env.cr.execute(
            '''UPDATE oomusic_playlist_line
               SET playing = False
               WHERE playlist_id = %s''', (self.playlist_id.id,))
        self.write({'playing': True})
        self.track_id.write({
            'last_play': fields.Datetime.now(),
            'play_count': self.track_id.play_count + 1,
        })
        if not self.playlist_id.current:
            playlists = self.env['oomusic.playlist'].search([('current', '=', True)])
            self.env.cr.execute(
                '''UPDATE oomusic_playlist_line
                   SET playing = False
                   WHERE playlist_id in %s''', (tuple(playlists.ids),))
            playlists.write({'current': False})
            playlists.playlist_line_ids.write({'playing': False})
            self.playlist_id.write({'current': True})
        return json.dumps(res)

    @api.multi
    def oomusic_play(self, seek=0):
        res = {}
        if not self:
            return json.dumps(res)

        res['playlist_line_id'] = self.id
        res.update(self.track_id._oomusic_info(seek=seek, norm=self.playlist_id.norm))
        return json.dumps(res)

    @api.multi
    def oomusic_previous(self, shuffle=False):
        res = {}
        # User might have removed the line from the playlist in the meantime => Fallback on first
        # track of playlist.
        try:
            lines = self.playlist_id.playlist_line_ids
        except MissingError:
            playlist = self.env['oomusic.playlist'].search([('current', '=', True)], limit=1)
            return playlist.playlist_line_ids[:1].oomusic_play()

        # Search for matching line, play first if end of list
        if shuffle:
            return self.oomusic_shuffle()
        try:
            idx = lines._ids.index(self._ids[0])
            if idx > 0:
                return lines[idx-1].oomusic_play()
            else:
                return lines[len(lines)-1].oomusic_play()
        except ValueError:
            pass
        return json.dumps(res)

    @api.multi
    def oomusic_next(self, shuffle=False):
        res = {}
        # User might have removed the line from the playlist in the meantime => Fallback on first
        # track of playlist.
        try:
            lines = self.playlist_id.playlist_line_ids
        except MissingError:
            playlist = self.env['oomusic.playlist'].search([('current', '=', True)], limit=1)
            return playlist.playlist_line_ids[:1].oomusic_play()

        # Search for matching line, play last if beginning of list
        if shuffle:
            return self.oomusic_shuffle()
        try:
            idx = lines._ids.index(self._ids[0])
            if idx < (len(lines) - 1):
                return lines[idx+1].oomusic_play()
            else:
                return lines[0].oomusic_play()
        except ValueError:
            pass
        return json.dumps(res)

    def oomusic_shuffle(self):
        lines = self.playlist_id.playlist_line_ids
        return lines[random.randint(0, len(lines)-1)].oomusic_play()

    def oomusic_last_track(self):
        playlist = self.env['oomusic.playlist'].search([('current', '=', True)], limit=1)
        if playlist and playlist.playlist_line_ids:
            playlist_line = playlist.playlist_line_ids.filtered(lambda r: r.playing is True)
            if not playlist_line:
                playlist_line = playlist.playlist_line_ids
            return playlist_line[0].oomusic_play()
        else:
            return json.dumps({})
