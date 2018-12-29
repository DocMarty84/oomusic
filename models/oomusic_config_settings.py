# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.release import version


class MusicConfigSettings(models.TransientModel):
    _name = 'oomusic.config.settings'
    _inherit = 'res.config.settings'

    cron = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string='Scheduled Actions', help='Activate automatic folder scan and image cache mechanism')
    view = fields.Selection([
        ('kanban', 'Kanban, with thumbnails'),
        ('tree', 'List, without thumbnails'),
    ], string='Default Views')
    ext_info = fields.Selection([
        ('auto', 'Fetched automatically'),
        ('manual', 'Fetched manually'),
    ], string='LastFM and Events Info')
    folder_sharing = fields.Selection([
        ('inactive', 'Inactive (user specific)'),
        ('active', 'Active (shared amongst all users)'),
    ], string='Folder Sharing')
    version = fields.Char('Version', readonly=True)

    @api.model
    def get_values(self):
        res = super(MusicConfigSettings, self).get_values()
        cron = (
            self.env.ref('oomusic.oomusic_scan_folder') +
            self.env.ref('oomusic.oomusic_build_artists_image_cache') +
            self.env.ref('oomusic.oomusic_build_image_cache') +
            self.env.ref('oomusic.oomusic_build_lastfm_cache')
        ).mapped('active')
        view = (
            self.env.ref('oomusic.action_album') +
            self.env.ref('oomusic.action_artist')
        ).mapped('view_mode')
        folder_sharing = (
            self.env.ref('oomusic.oomusic_album') +
            self.env.ref('oomusic.oomusic_artist') +
            self.env.ref('oomusic.oomusic_folder') +
            self.env.ref('oomusic.oomusic_genre') +
            self.env.ref('oomusic.oomusic_track')
        ).mapped('perm_read')
        res['cron'] = 'active' if all([c for c in cron]) else 'inactive'
        res['view'] = 'tree' if all([v.split(',')[0] == 'tree' for v in view]) else 'kanban'
        res['folder_sharing'] = 'inactive' if all([c for c in folder_sharing]) else 'active'
        res['ext_info'] = (
            self.env['ir.config_parameter'].sudo().get_param('oomusic.ext_info', 'auto'))
        res['version'] = version
        return res

    def set_values(self):
        super(MusicConfigSettings, self).set_values()
        # Activate/deactive ir.cron
        (
            self.env.ref('oomusic.oomusic_scan_folder') +
            self.env.ref('oomusic.oomusic_build_artists_image_cache') +
            self.env.ref('oomusic.oomusic_build_image_cache') +
            self.env.ref('oomusic.oomusic_build_bandsintown_cache') +
            self.env.ref('oomusic.oomusic_build_lastfm_cache')
        ).write({'active': bool(self.cron == 'active')})
        # Set view order
        if self.view == 'tree':
            view_mode_album = 'tree,kanban,form,graph,pivot'
            view_mode_artist = 'tree,kanban,form'
        else:
            view_mode_album = 'kanban,tree,form,graph,pivot'
            view_mode_artist = 'kanban,tree,form'
        self.env.ref('oomusic.action_album').write({'view_mode': view_mode_album})
        self.env.ref('oomusic.action_artist').write({'view_mode': view_mode_artist})
        # Set folder sharing
        (
            self.env.ref('oomusic.oomusic_album') +
            self.env.ref('oomusic.oomusic_artist') +
            self.env.ref('oomusic.oomusic_bandsintown_event') +
            self.env.ref('oomusic.oomusic_folder') +
            self.env.ref('oomusic.oomusic_genre') +
            self.env.ref('oomusic.oomusic_track')
        ).write({'perm_read': bool(self.folder_sharing == 'inactive')})
        if self.folder_sharing == 'inactive':
            self.env.cr.execute('''
                DELETE
                FROM oomusic_playlist_line
                WHERE id IN
                (
                    SELECT pl.id
                    FROM oomusic_playlist_line AS pl
                    JOIN oomusic_track AS t ON t.id = pl.track_id
                    WHERE t.user_id != pl.user_id
                )
            ''')
            self.env.cr.execute('''
                DELETE
                FROM oomusic_preference
                WHERE user_id != res_user_id
            ''')
        # Set LastFM Info
        self.env['ir.config_parameter'].sudo().set_param('oomusic.ext_info', self.ext_info)
