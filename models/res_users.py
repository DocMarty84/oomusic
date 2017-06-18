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
