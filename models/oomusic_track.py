# -*- coding: utf-8 -*-

from odoo import fields, models, api

class MusicTrack(models.Model):
    _name = 'oomusic.track'
    _description = 'Music Track'
    _order = 'artist_id, album_id, track_number'

    create_date = fields.Datetime(index=True)

    # ID3 Tags
    name = fields.Char('Title', required=True, index=True)
    artist_id = fields.Many2one('oomusic.artist', string='Artist', index=True)
    album_artist_id = fields.Many2one('oomusic.artist', string='Album Artist')
    album_id = fields.Many2one('oomusic.album', string='Album', index=True)
    disc = fields.Char('Disc')
    year = fields.Char('Year')
    track_number = fields.Char('Track #', index=True)
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
    play_count = fields.Integer('Play Count', default=0, index=True)
    last_play = fields.Datetime('Last Played', index=True)
    last_modification = fields.Integer('Last Modification')
    root_folder_id = fields.Many2one(
        'oomusic.folder', string='Root Folder', required=True, ondelete='cascade')
    folder_id = fields.Many2one(
        'oomusic.folder', string='Folder', required=True, ondelete='cascade')

    user_id = fields.Many2one(
        'res.users', string='User', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.user
    )
    playlist_line_ids = fields.One2many('oomusic.playlist.line', 'track_id', 'Playlist Line')
    in_playlist = fields.Boolean('In Current Playlist', compute='_compute_in_playlist')
    star = fields.Selection(
        [('0', 'Normal'), ('1', 'I Like It!')], 'Favorite', index=True, default='0')
    rating = fields.Selection(
        [('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
        'Rating', default='0',
    )

    @api.depends('playlist_line_ids')
    def _compute_in_playlist(self):
        if not self.env.context.get('compute_fields', True):
            return
        for track in self:
            track.in_playlist = bool(
                track.playlist_line_ids.mapped('playlist_id').filtered(lambda r: r.current is True))

    @api.multi
    def action_add_to_playlist(self):
        Playlist = self.env['oomusic.playlist'].search([('current', '=', True)], limit=1)
        if Playlist:
            Playlist._add_tracks(self)

    def _oomusic_info(self, seek=0):
        self.ensure_one()
        return {
            'title': self.artist_id.name + ' - ' + self.name if self.artist_id else self.name,
            'duration': self.duration,
            'image': self.album_id.image_medium,
            'mp3': '/oomusic/trans/' + str(self.id) + ('_%d' % (seek) if seek else '') + '.mp3',
            'oga': '/oomusic/trans/' + str(self.id) + ('_%d' % (seek) if seek else '') + '.ogg',
        }
