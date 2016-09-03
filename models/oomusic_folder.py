# -*- coding: utf-8 -*-

import base64
import imghdr
import logging
import os

from odoo import fields, models, api, tools

_logger = logging.getLogger(__name__)

class MusicFolder(models.Model):
    _name = 'oomusic.folder'
    _description = 'Music Folder'

    name = fields.Char('Name')
    root = fields.Boolean('Top Level Folder', default=True)
    path = fields.Char('Folder Path', required=True, index=True)
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
    image_small_kanban = fields.Binary(
        'Small-sized image', attachment=True,
        help='Image of the folder, used in Kanban view')


    _sql_constraints = [
        ('oomusic_folder_path_uniq', 'unique(path, user_id)', 'Folder path must be unique!'),
    ]

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
            resized_images = tools.image_get_resized_images(
                folder.image_folder, return_big=True, return_medium=False, return_small=False)
            folder.image_big = resized_images['image']

    @api.depends('image_folder')
    def _compute_image_medium(self):
        if not self.env.context.get('compute_fields', True):
            return
        for folder in self:
            resized_images = tools.image_get_resized_images(
                folder.image_folder, return_big=False, return_medium=True, return_small=False)
            folder.image_medium = resized_images['image_medium']

    @api.depends('image_folder')
    def _compute_image_small(self):
        if not self.env.context.get('compute_fields', True):
            return
        for folder in self:
            resized_images = tools.image_get_resized_images(
                folder.image_folder, return_big=False, return_medium=False, return_small=True)
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

    @api.multi
    def unlink(self):
        for folder in self:
            user_id = folder.user_id.id
            super(MusicFolder, folder).unlink()
            self.env['oomusic.folder.scan']._clean_tags(user_id)

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
        for folder in self.search([('root', '=', True)]):
            try:
                self.env['oomusic.folder.scan']._scan_folder(folder.id)
            except:
                continue

    @api.multi
    def action_build_kanban_cache(self):
        folder_id = self.id
        if folder_id:
            self.env['oomusic.folder.scan'].build_kanban_cache_th(folder_id)
