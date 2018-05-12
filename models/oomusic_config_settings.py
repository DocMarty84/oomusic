# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OomusicConfigSettings(models.TransientModel):
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
    fm_info = fields.Selection([
        ('auto', 'Fetched automatically'),
        ('manual', 'Fetched manually'),
    ], string='LastFM Info')

    @api.model
    def get_values(self):
        res = super(OomusicConfigSettings, self).get_values()
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
        res['cron'] = 'active' if all([c for c in cron]) else 'inactive'
        res['view'] = 'tree' if all([v.split(',')[0] == 'tree' for v in view]) else 'kanban'
        res['fm_info'] = self.env['ir.config_parameter'].sudo().get_param('oomusic.fm_info', 'auto')
        return res

    def set_values(self):
        super(OomusicConfigSettings, self).set_values()
        # Activate/deactive ir.cron
        (
            self.env.ref('oomusic.oomusic_scan_folder') +
            self.env.ref('oomusic.oomusic_build_artists_image_cache') +
            self.env.ref('oomusic.oomusic_build_image_cache') +
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
        # Set LastFM Info
        self.env['ir.config_parameter'].sudo().set_param('oomusic.fm_info', self.fm_info)
