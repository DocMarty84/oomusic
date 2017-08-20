# -*- coding: utf-8 -*-

import json
from urllib import urlencode

from odoo import fields, models, api, _
from odoo.exceptions import UserError, MissingError


class MusicTrack(models.Model):
    _name = 'oomusic.track'
    _description = 'Music Track'
    _order = 'album_id, disc, track_number_int, track_number'

    create_date = fields.Datetime(index=True)

    # ID3 Tags
    name = fields.Char('Title', required=True, index=True)
    artist_id = fields.Many2one('oomusic.artist', string='Artist', index=True)
    album_artist_id = fields.Many2one('oomusic.artist', string='Album Artist')
    album_id = fields.Many2one('oomusic.album', string='Album', index=True)
    disc = fields.Char('Disc')
    year = fields.Char('Year')
    track_number = fields.Char('Track #')
    track_number_int = fields.Integer('Track #')
    track_total = fields.Char('Total Tracks')
    genre_id = fields.Many2one('oomusic.genre', string='Genre')
    description = fields.Char('Description')
    composer = fields.Char('Composer')
    performer_id = fields.Many2one('oomusic.artist', string='Original Artist')
    copyright = fields.Char('Copyright')
    contact = fields.Char('Contact')
    encoded_by = fields.Char('Encoder')

    # File data
    duration = fields.Integer('Duration')
    duration_min = fields.Float('Duration')
    bitrate = fields.Integer('Bitrate')
    path = fields.Char('Path', required=True, index=True)
    play_count = fields.Integer('Play Count', default=0)
    last_play = fields.Datetime('Last Played', index=True)
    last_modification = fields.Integer('Last Modification')
    root_folder_id = fields.Many2one(
        'oomusic.folder', string='Root Folder', index=True, required=True, ondelete='cascade')
    folder_id = fields.Many2one(
        'oomusic.folder', string='Folder', index=True, required=True, ondelete='cascade')

    user_id = fields.Many2one(
        'res.users', string='User', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.user
    )
    playlist_line_ids = fields.One2many('oomusic.playlist.line', 'track_id', 'Playlist Line')
    in_playlist = fields.Boolean('In Current Playlist')
    star = fields.Selection(
        [('0', 'Normal'), ('1', 'I Like It!')], 'Favorite', default='0')
    rating = fields.Selection(
        [('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
        'Rating', default='0',
    )
    dummy_field = fields.Boolean('Dummy field')

    @api.multi
    def write(self, vals):
        res = super(MusicTrack, self).write(vals)
        if 'in_playlist' in vals:
            self.mapped('album_id')._compute_in_playlist()
        return res

    @api.multi
    def action_add_to_playlist(self):
        playlist = self.env['oomusic.playlist'].search([('current', '=', True)], limit=1)
        if not playlist:
            raise UserError(_('No current playlist found!'))
        if self.env.context.get('purge'):
            playlist.action_purge()
        playlist._add_tracks(self)

    @api.multi
    def action_download(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/oomusic/down/{}'.format(self.id),
            'target': 'new',
        }

    @api.multi
    def oomusic_play(self, seek=0):
        if not self:
            return json.dumps({})
        return json.dumps(self._oomusic_info(seek=seek))

    @api.multi
    def oomusic_star(self):
        try:
            self.write({'star': '1'})
        except MissingError:
            return
        return

    def _oomusic_info(self, seek=0, norm=False):
        self.ensure_one()
        params = {
            'seek': seek,
            'norm': 1 if norm else 0,
        }
        return {
            'track_id': self.id,
            'title': self.artist_id.name + ' - ' + self.name if self.artist_id else self.name,
            'duration': self.duration,
            'image': self.album_id.image_medium or self.artist_id.fm_image or '',
            'mp3': '/oomusic/trans/{}.mp3{}'.format(self.id, '?' + urlencode(params)),
            'oga': '/oomusic/trans/{}.ogg{}'.format(self.id, '?' + urlencode(params)),
            'opus': '/oomusic/trans/{}.opus{}'.format(self.id, '?' + urlencode(params)),
        }
