# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError

class MusicAlbum(models.Model):
    _name = 'oomusic.album'
    _description = 'Music Album'
    _order = 'year desc, name'

    create_date = fields.Datetime(index=True)

    name = fields.Char('Album', index=True)
    track_ids = fields.One2many('oomusic.track', 'album_id', 'Tracks')
    artist_id = fields.Many2one('oomusic.artist', 'Artist')
    genre_id = fields.Many2one('oomusic.genre', 'Genre')
    year = fields.Char('Year', index=True)
    folder_id = fields.Many2one('oomusic.folder', 'Folder', required=True, ondelete='cascade')
    user_id = fields.Many2one(
        'res.users', string='User', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.user
    )
    in_playlist = fields.Boolean('In Current Playlist', compute='_compute_in_playlist')
    star = fields.Selection(
        [('0', 'Normal'), ('1', 'I Like It!')], 'Favorite', index=True, default='0')

    image_folder = fields.Binary('Folder Image', related='folder_id.image_folder')
    image_big = fields.Binary("Big-sized image", related='folder_id.image_big')
    image_medium = fields.Binary("Medium-sized image", related='folder_id.image_medium')
    image_small = fields.Binary("Small-sized image", related='folder_id.image_small')
    image_small_kanban = fields.Binary("Small-sized image", related='folder_id.image_small_kanban')

    @api.depends('track_ids.in_playlist')
    def _compute_in_playlist(self):
        if not self.env.context.get('compute_fields', True):
            return
        for album in self:
            track_ids_in_playlist = album.track_ids.filtered(lambda r: r.in_playlist is True)
            if album.track_ids <= track_ids_in_playlist:
                album.in_playlist = True

    @api.multi
    def action_add_to_playlist(self):
        Playlist = self.env['oomusic.playlist'].search([('current', '=', True)], limit=1)
        if not Playlist:
            raise UserError(_('No current playlist found!'))
        for album in self:
            Playlist._add_tracks(album.track_ids)
