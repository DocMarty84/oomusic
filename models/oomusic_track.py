# -*- coding: utf-8 -*-

from hashlib import sha1
import json
import os
from shutil import copyfile
from tempfile import gettempdir
from time import sleep
from urllib.parse import urlencode
from zipfile import ZipFile

from odoo import fields, models, api, _
from odoo.exceptions import UserError, MissingError


class MusicTrack(models.Model):
    _name = 'oomusic.track'
    _description = 'Music Track'
    _order = 'album_id, disc, track_number_int, track_number'
    _inherit = ['oomusic.download.mixin']

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
    duration = fields.Integer('Duration', readonly=True)
    duration_min = fields.Float('Duration', readonly=True)
    bitrate = fields.Integer('Bitrate', readonly=True)
    path = fields.Char('Path', required=True, index=True, readonly=True)
    play_count = fields.Integer('Play Count', default=0, readonly=True)
    last_play = fields.Datetime('Last Played', index=True, readonly=True)
    last_modification = fields.Integer('Last Modification', readonly=True)
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

    def _get_track_ids(self):
        return self

    def _build_zip(self, flatten=False, name=False):
        # Name is build using track ids, to avoid creating the same archive twice
        name = '-'.join([str(id) for id in self.mapped('id')]) + ('-1' if flatten else '-0')
        name = sha1(name.encode('utf-8')).hexdigest()
        tmp_dir = gettempdir()
        z_name = os.path.join(tmp_dir, '{}.zip'.format(name))

        # If file exists return it instead of creating a new archive
        if os.path.isfile(z_name):
            return z_name

        # Create the ZIP file
        seq = 1
        with ZipFile(z_name, 'w') as z_file:
            base_arcname = '{:0%sd}-{}' % len(str(len(self)))
            for track in self:
                if flatten:
                    arcname = base_arcname.format(seq, os.path.split(track.path)[1])
                    path = os.path.join(tmp_dir, arcname)
                    copyfile(track.path, path)
                    z_file.write(path, arcname=arcname)
                    os.remove(path)
                    seq += 1
                else:
                    path = track.path
                    arcname = track.path.replace(track.root_folder_id.path, '')
                    z_file.write(path, arcname=arcname)
        sleep(0.2)
        return z_name

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

    def _oomusic_info(self, seek=0, norm=False, raw=False):
        self.ensure_one()
        params = {
            'seek': seek,
            'norm': 1 if norm else 0,
            'raw': 1,
        }
        raw_src = ['/oomusic/trans/{}.{}?{}'.format(
            self.id, os.path.splitext(self.path)[1][1:], urlencode(params)
        )] if raw else []

        params['raw'] = 0
        return {
            'track_id': self.id,
            'title': (
                u'{} - {}'.format(self.artist_id.name, self.name) if self.artist_id else self.name
            ),
            'duration': self.duration,
            'image': (
                (self.album_id.image_medium or self.artist_id.fm_image or b'').decode('utf-8')
                if not self.env.context.get('test_mode')
                else 'TEST'
            ),
            'src': raw_src + [
                '/oomusic/trans/{}.{}?{}'.format(self.id, ext, urlencode(params))
                for ext in ['opus', 'ogg', 'mp3']
            ],
        }

    def _lastfm_track_getsimilar(self, count=50):
        self.ensure_one()
        url = 'https://ws.audioscrobbler.com/2.0/?method=track.getsimilar&artist='\
            + self.artist_id.name + '&track=' + self.name + '&limit=' + str(count)
        return json.loads(self.env['oomusic.lastfm'].get_query(url))
