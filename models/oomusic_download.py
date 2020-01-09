# -*- coding: utf-8 -*-

import uuid
from datetime import datetime, timedelta

from werkzeug.urls import url_encode

from odoo import api, fields, models


class MusicDownload(models.Model):

    _name = "oomusic.download"
    _rec_name = "access_token"
    _order = "expiration_date desc, id desc"
    _description = "Download links"

    def _default_access_token(self):
        return uuid.uuid4().hex

    def _default_expiration_date(self):
        return fields.Date.to_string((datetime.now() + timedelta(days=30)).date())

    res_model_id = fields.Many2one(
        "ir.model",
        "Related Document Model",
        ondelete="cascade",
        help="Model of the followed resource",
    )
    res_model = fields.Char(
        string="Document Model", related="res_model_id.model", store=True, readonly=True
    )
    res_id = fields.Integer(
        string="Document", required=True, help="Identifier of the downloaded object"
    )
    access_token = fields.Char(
        "Security Token",
        index=True,
        default=lambda s: s._default_access_token(),
        help="Access token to access the files",
    )
    note = fields.Char("Comment")
    flatten = fields.Boolean(
        "Flatten", help="If activated, all tracks will be in the root folder of the ZIP file."
    )
    expiration_date = fields.Date(
        "Expiration Date",
        index=True,
        default=lambda s: s._default_expiration_date(),
        help="The link will be deactivated after this date.",
    )
    min_delay = fields.Integer(
        "Minimum Delay", default=60, help="Minimum delay in seconds between consecutive accesses."
    )
    access_date = fields.Datetime("Last Access Date")
    url = fields.Char(
        "URL",
        compute="_compute_url",
        help="Send this URL to your contacts so they will download the tracks.",
    )
    expired = fields.Boolean("Expired", compute="_compute_expired")
    user_id = fields.Many2one(
        "res.users",
        string="User",
        index=True,
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.user,
    )

    @api.depends("access_token")
    def _compute_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for down in self:
            params = {"token": down.access_token}
            down.url = "{}/oomusic/down?{}".format(base_url, url_encode(params))

    def _compute_expired(self):
        for down in self:
            down.expired = bool(down.expiration_date < fields.Date.today())

    def _update_access_date(self, date):
        self.write({"access_date": date})
        self.env.cr.commit()


class MusicDownloadMixin(models.AbstractModel):
    _name = "oomusic.download.mixin"
    _description = "Download Mixin"

    download_ids = fields.One2many(
        "oomusic.download",
        "res_id",
        string="Download Links",
        domain=lambda self: [("res_model", "=", self._name)],
        auto_join=True,
    )

    def _get_track_ids(self):
        return self.track_ids

    def unlink(self):
        """ When removing a record, its rating should be deleted too. """
        rec_ids = self.ids
        res = super(MusicDownloadMixin, self).unlink()
        self.env["oomusic.download"].sudo().search(
            [("res_model", "=", self._name), ("res_id", "in", rec_ids)]
        ).unlink()
        return res

    def action_create_download_link(self):
        for obj in self:
            record_model_id = (
                self.env["ir.model"].sudo().search([("model", "=", obj._name)], limit=1).id
            )
            self.env["oomusic.download"].create({"res_model_id": record_model_id, "res_id": obj.id})
        return True

    def action_download(self):
        params = {
            "model": self._name,
            "id": self.id,
            "flatten": 1 if self._name in ["oomusic.track", "oomusic.playlist"] else 0,
        }
        return {
            "type": "ir.actions.act_url",
            "url": "/oomusic/down_user?{}".format(url_encode(params)),
            "target": "new",
        }
