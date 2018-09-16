# -*- coding: utf-8 -*-

import json
import random

from odoo import fields, models, api, _
from odoo.exceptions import MissingError, ValidationError


class MusicPlaylist(models.Model):
    _name = 'oomusic.playlist'
    _description = 'Music Playlist'
    _inherit = ['oomusic.download.mixin']

    def _default_current(self):
        return not bool(self.env['oomusic.playlist'].search([('current', '=', True)]))

    name = fields.Char('Name', required="1")
    user_id = fields.Many2one(
        'res.users', string='User', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.user
    )
    comment = fields.Char('Comment')
    current = fields.Boolean('Current', default=lambda self: self._default_current(), copy=False)
    norm = fields.Boolean(
        'Normalize', default=False,
        help='Normalize playlist loudness thanks to the EBU R128 normalization. It requires '
             'FFmpeg >=3.2.1 which includes by default the appropriate library (libebur128).\n'
             'Transcoding will be significantly slower when activated, implying larger gaps between'
             ' songs.'
    )
    raw = fields.Boolean(
        'No Transcoding', default=False,
        help='Do not transcode audio files. It decreases the server load, '
             'at the cost of a higher network usage.'
    )
    audio = fields.Selection(
        [('html', 'HTML5 Audio'), ('web', 'Web Audio API')], 'Audio API', default='html',
        help='API used for audio playback.\n'
             '- HTML5 Audio: no need to download the full file before starting the playback.\n'
             '- Web Audio API: need to download the full file before starting the playback. More \n'
             'reliable than HTML5, but longer gaps between tracks.'
    )
    playlist_line_ids = fields.One2many(
        'oomusic.playlist.line', 'playlist_id', string='Tracks', copy=True)
    album_id = fields.Many2one(
        'oomusic.album', string='Add Album Tracks', store=False,
        help='Encoding help. When selected, the associated album tracks are added to the playlist.')
    artist_id = fields.Many2one(
        'oomusic.artist', string='Add Artist Tracks', store=False,
        help='Encoding help. When selected, the associated artist tracks are added to the playlist.')
    smart_playlist = fields.Selection([
        ('rnd', 'Random Tracks'),
        ('played', 'Already Played'),
        ('not_played', 'Never Played'),
        ('most_played', 'Most Played'),
        ('last_listened', 'Last Listened'),
        ('recent', 'Recent'),
        ('favorite', 'Favorites'),
        ('best_rated', 'Best Rated'),
        ('worst_rated', 'Worst Rated'),
    ], 'Smart Playlist')
    smart_playlist_qty = fields.Integer('Quantity To Add', default=20)

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

    def _get_track_ids(self):
        return self.playlist_line_ids.mapped('track_id')

    @api.onchange('album_id')
    def _onchange_album_id(self):
        self._add_tracks(self.album_id.track_ids, onchange=True)
        self.album_id = False
        return {}

    @api.onchange('artist_id')
    def _onchange_artist_id(self, onchange=True):
        self._add_tracks(self.artist_id.track_ids, onchange=True)
        self.artist_id = False
        return {}

    @api.onchange('audio')
    def _onchange_audio(self):
        self.raw = True if self.audio == 'web' else False

    @api.onchange('smart_playlist')
    def _onchange_smart_playlist(self):
        if not self.smart_playlist:
            return
        if self.smart_playlist_qty < 1:
            self.smart_playlist_qty = 20
        tracks = getattr(self, '_smart_{}'.format(self.smart_playlist))()
        self._add_tracks(tracks, onchange=True)
        self.smart_playlist = False

    @api.constrains('norm', 'raw')
    def _check_norm_raw(self):
        for playlist in self:
            if playlist.norm and playlist.raw:
                raise ValidationError(_(
                    "'Normalize' and 'No Transcoding' are mutually exclusive options. Please "
                    "activate only one of the two options."
                ))

    @api.multi
    def unlink(self):
        track_ids = self.playlist_line_ids.mapped('track_id')
        res = super(MusicPlaylist, self).unlink()
        track_ids.write({'in_playlist': False})
        return res

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
            UPDATE oomusic_preference SET in_playlist = false
            WHERE user_id = %s
                AND in_playlist = true
                AND res_model = 'oomusic.track'
            ''', (self.env.uid, ))
        self.env.cr.execute('''
            UPDATE oomusic_preference SET in_playlist = false
            WHERE user_id = %s
                AND in_playlist = true
                AND res_model = 'oomusic.album'
            ''', (self.env.uid, ))

        # Recompute 'in_playlist' field
        self.playlist_line_ids.mapped('track_id').write({'in_playlist': True})

    def _smart_rnd(self):
        current_tracks = self.playlist_line_ids.mapped('track_id')
        folder_sharing = (
            'inactive' if self.env.ref('oomusic.oomusic_track').sudo().perm_read else 'active'
        )
        query = 'SELECT id FROM oomusic_track '
        if current_tracks:
            query += 'WHERE id NOT IN %s' % (tuple(current_tracks.ids + [0]),)
        if folder_sharing == 'inactive':
            query += '{} user_id = {}'.format(
                'WHERE' if not current_tracks else 'AND', self.env.uid)
        self.env.cr.execute(query)
        res = self.env.cr.fetchall()
        if not res:
            return self.env['oomusic.track']

        track_ids = random.sample([r[0] for r in res], min(self.smart_playlist_qty, len(res)))
        return self.env['oomusic.track'].browse(track_ids)

    def _smart_played(self):
        current_tracks = self.playlist_line_ids.mapped('track_id')
        return self.env['oomusic.track'].search([
            ('play_count', '>', 0), ('id', 'not in', current_tracks.ids)
        ], limit=self.smart_playlist_qty)

    def _smart_not_played(self):
        current_tracks = self.playlist_line_ids.mapped('track_id')
        return self.env['oomusic.track'].search([
            ('play_count', '=', 0), ('id', 'not in', current_tracks.ids)
        ], limit=self.smart_playlist_qty)

    def _smart_most_played(self):
        # order on a non-stored field is not supported, even if there is a search method. Therefore,
        # we directly search on oomusic.preference.
        current_tracks = self.playlist_line_ids.mapped('track_id')
        res_ids = [p['res_id'] for p in self.env['oomusic.preference'].search([
            ('play_count', '>', 0),
            ('res_model', '=', 'oomusic.track'),
            ('res_id', 'not in', current_tracks.ids),
        ], limit=self.smart_playlist_qty, order='play_count DESC').read(['res_id'])]
        return self.env['oomusic.track'].browse(res_ids)

    def _smart_last_listened(self):
        current_tracks = self.playlist_line_ids.mapped('track_id')
        res_ids = [p['res_id'] for p in self.env['oomusic.preference'].search([
            ('last_play', '!=', False),
            ('res_model', '=', 'oomusic.track'),
            ('res_id', 'not in', current_tracks.ids),
        ], limit=self.smart_playlist_qty, order='last_play DESC').read(['res_id'])]
        return self.env['oomusic.track'].browse(res_ids)

    def _smart_recent(self):
        current_tracks = self.playlist_line_ids.mapped('track_id')
        return self.env['oomusic.track'].search([
            ('id', 'not in', current_tracks.ids)
        ], limit=self.smart_playlist_qty,
        order='create_date DESC, ' + self.env['oomusic.track']._order)

    def _smart_favorite(self):
        current_tracks = self.playlist_line_ids.mapped('track_id')
        return self.env['oomusic.track'].search([
            ('star', '=', '1'), ('id', 'not in', current_tracks.ids)
        ], limit=self.smart_playlist_qty)

    def _smart_best_rated(self):
        current_tracks = self.playlist_line_ids.mapped('track_id')
        res_ids = [p['res_id'] for p in self.env['oomusic.preference'].search([
            ('res_model', '=', 'oomusic.track'),
            ('res_id', 'not in', current_tracks.ids),
        ], limit=self.smart_playlist_qty, order='rating DESC').read(['res_id'])]
        return self.env['oomusic.track'].browse(res_ids)

    def _smart_worst_rated(self):
        current_tracks = self.playlist_line_ids.mapped('track_id')
        return self.env['oomusic.track'].search([
            ('id', 'not in', current_tracks.ids)
        ], limit=self.smart_playlist_qty,
        order='rating, ' + self.env['oomusic.track']._order)


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
        res['audio'] = self.playlist_id.audio
        track_info = self.track_id._oomusic_info(
            seek=seek, norm=self.playlist_id.norm, raw=self.playlist_id.raw
        )
        res.update(track_info)
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
