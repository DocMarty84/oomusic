# -*- coding: utf-8 -*-

import base64
import uuid
from io import BytesIO

import qrcode

from odoo import api, fields, models


class MusicRemote(models.Model):
    _name = "oomusic.remote"
    _description = "Remote Control"

    def _default_name(self):
        return fields.Date.to_string(fields.Date.context_today(self))

    def _default_access_token(self):
        return uuid.uuid4().hex

    name = fields.Char("Name", default=lambda s: s._default_name())
    access_token = fields.Char(
        "Access Token", index=True, default=lambda s: s._default_access_token()
    )
    public = fields.Boolean("Public", default=False)
    url = fields.Char(
        "URL", compute="_compute_url", help="Access this URL to control the playback remotely."
    )
    qr = fields.Binary("QR Code", compute="_compute_qr", help="QR code pointing to the remote URL.")
    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.user,
    )

    @api.depends("access_token", "public")
    def _compute_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for remote in self:
            remote.url = "{}/oomusic/remote{}/{}".format(
                base_url, "_public" if remote.public else "", remote.access_token
            )

    @api.depends("url")
    def _compute_qr(self):
        for remote in self:
            img = qrcode.make(remote.url)
            img_tmp = BytesIO()
            img.save(img_tmp, format="PNG")
            remote.qr = base64.b64encode(img_tmp.getvalue())

    def action_reset_remote_token(self):
        for remote in self:
            remote.access_token = uuid.uuid4().hex
