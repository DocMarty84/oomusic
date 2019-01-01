# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    latitude = fields.Float('Latitude', digits=0)
    longitude = fields.Float('Longitude', digits=0)
    max_distance = fields.Float(
        'Events Maximum Distance (km)',
        help='Display events located at this maximum distance from your location. '
             'Set to zero to show all events.'
    )

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on latitude, longitude and max_distance.
            Access rights are disabled by default, but allowed on some specific fields defined in
            self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(ResUsers, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        type(self).SELF_WRITEABLE_FIELDS.extend(['latitude', 'longitude', 'max_distance'])
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        type(self).SELF_READABLE_FIELDS.extend(['latitude', 'longitude', 'max_distance'])
        return init_res

    @api.model
    def create(self, vals):
        User = super(ResUsers, self).create(vals)
        self.env['oomusic.playlist'].sudo().create({
            'name': _("My Playlist"),
            'user_id': User.id,
            'current': True,
        })
        return User

    @api.multi
    def unlink(self):
        # Manually unlink the root folder to trigger the deletion of all children and tracks. This
        # is really necessary, but performance-wise this has a major impact.
        self.env['oomusic.folder'].sudo().search(
            [('root', '=', True), ('user_id', 'in', self.ids)]).unlink()
        super(ResUsers, self).unlink()
