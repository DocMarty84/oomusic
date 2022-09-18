# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    latitude = fields.Float("Latitude", digits=0)
    longitude = fields.Float("Longitude", digits=0)
    max_distance = fields.Float(
        "Events Maximum Distance (km)",
        help="Display events located at this maximum distance from your location. "
        "Set to zero to show all events.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["latitude", "longitude", "max_distance"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["latitude", "longitude", "max_distance"]

    @api.model_create_multi
    def create(self, vals_list):
        users = super(ResUsers, self).create(vals_list)
        for user in users:
            self.env["oomusic.playlist"].sudo().create(
                {"name": _("My Playlist"), "user_id": user.id, "current": True}
            )
        return users

    def unlink(self):
        # Manually unlink the root folder to trigger the deletion of all children and tracks. This
        # is really necessary, but performance-wise this has a major impact.
        self.env["oomusic.folder"].sudo().search(
            [("root", "=", True), ("user_id", "in", self.ids)]
        ).unlink()
        super(ResUsers, self).unlink()
