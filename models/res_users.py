# -*- coding: utf-8 -*-

from odoo import models, api, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals):
        User = super(ResUsers, self).create(vals)
        self.env['oomusic.playlist'].create({
            'name': _("My Playlist"),
            'user_id': User.id,
            'current': True,
        })
        return User

    @api.multi
    def unlink(self):
        # Manually unlink the root folder to trigger the deletion of all children and tracks. This
        # is really necessary, but performance-wise this has a major impact.
        self.env['oomusic.folder'].search(
            [('root', '=', True), ('user_id', 'in', self.ids)]).unlink()
        super(ResUsers, self).unlink()
