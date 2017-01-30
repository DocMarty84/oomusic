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
    star = fields.Selection(
        [('0', 'Normal'), ('1', 'I Like It!')], 'Favorite', index=True, default='0')
    rating = fields.Selection(
        [('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
        'Rating', default='0',
    )

    image_folder = fields.Binary(
        'Folder Image', compute='_compute_image_folder',
        help='This field holds the image used as image for the folder, limited to 1024x1024px.')
    image_big = fields.Binary(
        'Big-sized image', compute='_compute_image_big', inverse='_set_image_big',
        help='Image of the folder. It is automatically resized as a 1024x1024px image, with aspect '
        'ratio preserved.')
    image_big_cache = fields.Binary(
        'Big-sized image', attachment=True,
        help='Image of the folder. It is automatically resized as a 1024x1024px image, with aspect '
        'ratio preserved.')
    image_medium = fields.Binary(
        'Medium-sized image', compute='_compute_image_medium', inverse='_set_image_medium',
        help='Image of the folder.')
    image_medium_cache = fields.Binary(
        'Medium-sized image', attachment=True,
        help='Image of the folder')
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
        for folder in self:
            if folder.root:
                folder.path_name = folder.path
            else:
                folder.path_name = folder.path.split(os.sep)[-1]

    @api.depends('track_ids.in_playlist')
    def _compute_in_playlist(self):
        for folder in self:
            track_ids_in_playlist = folder.track_ids.filtered(lambda r: r.in_playlist is True)
            if folder.track_ids <= track_ids_in_playlist:
                folder.in_playlist = True

    def _compute_image_folder(self):
        accepted_names = ['folder', 'cover', 'front']
        for folder in self:
            _logger.debug("Computing image folder %s...", folder.path)

            # Keep image files only
            files = [
                f for f in os.listdir(folder.path)
                if os.path.isfile(os.path.join(folder.path, f))\
                    and imghdr.what(os.path.join(folder.path, f))
            ]

            # Try to find an image with a name matching the accepted names
            folder.image_folder = False
            for f in files:
                for n in accepted_names:
                    if n in f.lower():
                        with open(os.path.join(folder.path, f), 'r') as img:
                            folder.image_folder = base64.b64encode(img.read())
                            break

                if folder.image_folder:
                    break

    @api.depends('image_folder')
    def _compute_image_big(self):
        for folder in self:
            if folder.image_big_cache and not self.env.context.get('build_cache'):
                folder.image_big = folder.image_big_cache
                continue
            try:
                _logger.debug("Resizing image folder %s...", folder.path)
                resized_images = tools.image_get_resized_images(
                    folder.image_folder, return_big=True, return_medium=False, return_small=False)
            except:
                _logger.warning('Error with image in folder "%s"', folder.path)
                continue

            folder.image_big = resized_images['image']

            # Save in cache
            new_cr = self.pool.cursor()
            new_self = self.with_env(self.env(cr=new_cr))
            new_self.env['oomusic.folder'].browse(folder.id).sudo().write({
                'image_big_cache': resized_images['image'],
            })
            new_self.env.cr.commit()
            new_self.env.cr.close()

    @api.depends('image_folder')
    def _compute_image_medium(self):
        for folder in self:
            if folder.image_medium_cache and not self.env.context.get('build_cache'):
                folder.image_medium = folder.image_medium_cache
                continue
            try:
                _logger.debug("Resizing image folder %s...", folder.path)
                resized_images = tools.image_get_resized_images(
                    folder.image_folder, return_big=False, return_medium=True, return_small=False)
            except:
                _logger.warning('Error with image in folder "%s"', folder.path)
                continue

            folder.image_medium = resized_images['image_medium']

            # Save in cache
            new_cr = self.pool.cursor()
            new_self = self.with_env(self.env(cr=new_cr))
            new_self.env['oomusic.folder'].browse(folder.id).sudo().write({
                'image_medium_cache': resized_images['image_medium'],
            })
            new_self.env.cr.commit()
            new_self.env.cr.close()

    @api.depends('image_folder')
    def _compute_image_small(self):
        for folder in self:
            if folder.image_small_cache and not self.env.context.get('build_cache'):
                folder.image_small = folder.image_small_cache
                continue
            try:
                _logger.debug("Resizing image folder %s...", folder.path)
                resized_images = tools.image_get_resized_images(
                    folder.image_folder, return_big=False, return_medium=False, return_small=True)
            except:
                _logger.warning('Error with image in folder "%s"', folder.path)
                continue

            folder.image_small = resized_images['image_small']

            # Save in cache
            new_cr = self.pool.cursor()
            new_self = self.with_env(self.env(cr=new_cr))
            new_self.env['oomusic.folder'].browse(folder.id).sudo().write({
                'image_small_cache': resized_images['image_small'],
            })
            new_self.env.cr.commit()
            new_self.env.cr.close()

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
            folders = self | self.search([('id', 'child_of', self.ids)])
            folders.write({'last_modification': 0})
            tracks = folders.mapped('track_ids')
            tracks.write({'last_modification': 0})
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

    @api.multi
    def action_scan_folder_full(self):
        '''
        This is a method used to force a full scan of a folder.
        '''
        folder_id = self.id
        if folder_id:
            # Set the last modification date to zero so we force scanning all folders and files
            new_cr = self.pool.cursor()
            new_self = self.with_env(self.env(cr=new_cr))
            folders = new_self.env['oomusic.folder'].search([('id', 'child_of', self.ids)]) | self
            folders.write({'last_modification': 0})
            tracks = folders.mapped('track_ids')
            tracks.write({'last_modification': 0})
            new_self.env.cr.commit()
            new_self.env.cr.close()

            self.env['oomusic.folder.scan'].scan_folder_th(folder_id)

    @api.model
    def cron_scan_folder(self):
        for folder in self.search([('root', '=', True), ('exclude_autoscan', '=', False)]):
            try:
                self.env['oomusic.folder.scan']._scan_folder(folder.id)
            except:
                continue

    @api.model
    def cron_build_image_cache(self):
        # Do not loop on folders to avoid prefetching image_folder for all elements. This won't work
        # since the size of prefetched data will be larger than the maximum cache size (I guess).
        folders = self.search([])
        for i in xrange(0, len(folders)):
            folder = folders[i]
            folder.with_context(build_cache=True, prefetch_fields=False)._compute_image_big()
            folder.with_context(build_cache=True, prefetch_fields=False)._compute_image_medium()
            folder.with_context(build_cache=True, prefetch_fields=False)._compute_image_small()

    @api.multi
    def action_add_to_playlist(self):
        Playlist = self.env['oomusic.playlist'].search([('current', '=', True)], limit=1)
        if not Playlist:
            raise UserError(_('No current playlist found!'))
        for folder in self:
            Playlist._add_tracks(folder.track_ids)
