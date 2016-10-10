# -*- coding: utf-8 -*-

import base64
import imghdr
import logging
import os

from odoo import fields, models, api, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class MusicFolder(models.Model):
    _name = 'oomusic.folder'
    _description = 'Music Folder'
    _order = 'path'

    name = fields.Char('Name')
    root = fields.Boolean('Top Level Folder', default=True)
    path = fields.Char('Folder Path', required=True, index=True)
    exclude_autoscan = fields.Boolean(
        'No auto-scan', default=False,
        help='Exclude this folder from the automatized scheduled scan. Useful if the folder is not '
        'always accessible, e.g. linked to an external drive.'
    )
    has_cover_art = fields.Boolean(compute='_compute_image_folder', store=True)
    last_scan = fields.Datetime('Last Scanned')
    last_scan_duration = fields.Integer('Scan Duration (s)')
    parent_id = fields.Many2one('oomusic.folder', string='Parent Folder', ondelete='cascade')
    child_ids = fields.One2many('oomusic.folder', 'parent_id', string='Child Folders')
    user_id = fields.Many2one(
        'res.users', string='User', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.user
    )
    last_modification = fields.Integer('Last Modification')
    locked = fields.Boolean(
        'Locked', default=False,
        help='When a folder is being scanned, it is flagged as "locked". It might be necessary to '
        'unlock it manually if scanning has failed or has been interrupted.')

    path_name = fields.Char('Folder Name', compute='_compute_path_name')
    in_playlist = fields.Boolean('In Current Playlist', compute='_compute_in_playlist')
    track_ids = fields.One2many('oomusic.track', 'folder_id', 'Tracks')

    image_folder = fields.Binary(
        'Folder Image', compute='_compute_image_folder',
        help='This field holds the image used as image for the folder, limited to 1024x1024px.')
    image_big = fields.Binary(
        'Big-sized image', compute='_compute_image_big', inverse='_set_image_big',
        help='Image of the folder. It is automatically resized as a 1024x1024px image, with aspect '
        'ratio preserved.')
    image_medium = fields.Binary(
        'Medium-sized image', compute='_compute_image_medium', inverse='_set_image_medium',
        help='Image of the folder.')
    image_small = fields.Binary(
        'Small-sized image', compute='_compute_image_small', inverse='_set_image_small',
        help='Image of the folder.')
    image_small_cache = fields.Binary(
        'Small-sized image', attachment=True,
        help='Image of the folder, used in Kanban view')


    _sql_constraints = [
        ('oomusic_folder_path_uniq', 'unique(path, user_id)', 'Folder path must be unique!'),
    ]

    @api.depends('path')
    def _compute_path_name(self):
        if not self.env.context.get('compute_fields', True):
            return
        for folder in self:
            if folder.root:
                folder.path_name = folder.path
            else:
                folder.path_name = folder.path.split(os.sep)[-1]

    @api.depends('track_ids.in_playlist')
    def _compute_in_playlist(self):
        if not self.env.context.get('compute_fields', True):
            return
        for folder in self:
            track_ids_in_playlist = folder.track_ids.filtered(lambda r: r.in_playlist is True)
            if folder.track_ids <= track_ids_in_playlist:
                folder.in_playlist = True

    @api.depends('name')
    def _compute_image_folder(self):
        if not self.env.context.get('compute_fields', True):
            return
        for folder in self:
            accepted_names = ['folder', 'cover', 'front']
            files = [
                f for f in os.listdir(folder.path)
                if os.path.isfile(os.path.join(folder.path, f))\
                    and imghdr.what(os.path.join(folder.path, f))
            ]
            for f in files:
                for n in accepted_names:
                    if n in f.lower():
                        with open(os.path.join(folder.path, f), 'r') as img:
                            folder.image_folder = base64.b64encode(img.read())
                            folder.has_cover_art = True
                            return
            folder.image_folder = False

    @api.depends('image_folder')
    def _compute_image_big(self):
        if not self.env.context.get('compute_fields', True):
            return
        for folder in self:
            try:
                resized_images = tools.image_get_resized_images(
                    folder.image_folder, return_big=True, return_medium=False, return_small=False)
            except:
                _logger.warning('Error with image in folder "%s"', folder.path)
                return
            folder.image_big = resized_images['image']

    @api.depends('image_folder')
    def _compute_image_medium(self):
        if not self.env.context.get('compute_fields', True):
            return
        for folder in self:
            try:
                resized_images = tools.image_get_resized_images(
                    folder.image_folder, return_big=False, return_medium=True, return_small=False)
            except:
                _logger.warning('Error with image in folder "%s"', folder.path)
                return
            folder.image_medium = resized_images['image_medium']

    @api.depends('image_folder')
    def _compute_image_small(self):
        if not self.env.context.get('compute_fields', True):
            return
        for folder in self:
            if folder.image_small_cache:
                folder.image_small = folder.image_small_cache
                return

            try:
                resized_images = tools.image_get_resized_images(
                    folder.image_folder, return_big=False, return_medium=False, return_small=True)
            except:
                _logger.warning('Error with image in folder "%s"', folder.path)
                return
            folder.image_small = resized_images['image_small']

    def _set_image_big(self):
        for folder in self:
            folder._set_image_value(folder.image_big)

    def _set_image_medium(self):
        for folder in self:
            folder._set_image_value(folder.image_medium)

    def _set_image_small(self):
        for folder in self:
            folder._set_image_value(folder.image_small)

    def _set_image_value(self, value):
        for folder in self:
            folder.image_folder = tools.image_resize_image_big(value)

    @api.model
    def create(self, vals):
        if 'path' in vals and vals.get('root', True):
            vals['path'] = os.path.normpath(vals['path'])
        return super(MusicFolder, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'path' in vals:
            vals['path'] = os.path.normpath(vals['path'])
        return super(MusicFolder, self).write(vals)

    @api.multi
    def unlink(self):
        user_ids = self.mapped('user_id')
        super(MusicFolder, self).unlink()
        for user_id in user_ids:
            self.env['oomusic.folder.scan']._clean_tags(user_id.id)

    @api.multi
    def action_scan_folder(self):
        '''
        This is the main method used to scan a oomusic folder. It creates a thread with the scanning
        process.
        '''
        folder_id = self.id
        if folder_id:
            self.env['oomusic.folder.scan'].scan_folder_th(folder_id)

    @api.model
    def cron_scan_folder(self):
        for folder in self.search([('root', '=', True), ('exclude_autoscan', '=', False)]):
            try:
                self.env['oomusic.folder.scan']._scan_folder(folder.id)
            except:
                continue

    @api.multi
    def action_build_image_cache(self):
        folder_id = self.id
        if folder_id:
            self.env['oomusic.folder.scan'].build_kanban_cache_th(folder_id)

    @api.model
    def cron_build_image_cache(self):
        for folder in self.search([('root', '=', True), ('exclude_autoscan', '=', False)]):
            try:
                self.env['oomusic.folder.scan']._build_image_cache(folder.id)
            except:
                continue

    @api.multi
    def action_add_to_playlist(self):
        Playlist = self.env['oomusic.playlist'].search([('current', '=', True)], limit=1)
        if not Playlist:
            raise UserError(_('No current playlist found!'))
        for folder in self:
            Playlist._add_tracks(folder.track_ids)
