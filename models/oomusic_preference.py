# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MusicPreference(models.Model):
    _name = "oomusic.preference"
    _rec_name = "res_model"
    _order = "id"
    _description = "User Preferences"

    res_model_id = fields.Many2one(
        "ir.model",
        "Related Document Model",
        ondelete="cascade",
        help="Model of the preference resource",
    )
    res_model = fields.Char(
        string="Document Model", related="res_model_id.model", store=True, readonly=True
    )
    res_id = fields.Integer(
        string="Document", required=True, help="Identifier of the preference object"
    )
    res_user_id = fields.Many2one(
        "res.users", string="Document User", index=True, required=True, ondelete="cascade"
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        index=True,
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.user,
    )
    play_count = fields.Integer("Play Count", default=0, readonly=True)
    last_play = fields.Datetime("Last Played", index=True, readonly=True)
    star = fields.Selection([("0", "Normal"), ("1", "I Like It!")], "Favorite", default="0")
    rating = fields.Selection(
        [("0", "0"), ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5")],
        "Rating",
        default="0",
    )
    bit_follow = fields.Selection(
        [("normal", "Not Followed"), ("done", "Followed")], "Follow Events", default="normal"
    )
    tag_ids = fields.Many2many("oomusic.tag", string="Custom Tags")


class MusicPreferenceMixin(models.AbstractModel):
    _name = "oomusic.preference.mixin"
    _description = "Download Mixin"

    pref_ids = fields.One2many(
        "oomusic.preference",
        "res_id",
        string="User Preferences",
        domain=lambda self: [
            ("res_model", "=", self._name),
            ("user_id", "=", self.env.context.get("default_user_id", self.env.user.id)),
        ],
        auto_join=True,
    )

    @api.depends("pref_ids")
    def _compute_play_count(self):
        for obj in self:
            obj.play_count = obj._get_pref("play_count")

    def _inverse_play_count(self):
        for obj in self:
            obj._set_pref({"play_count": obj.play_count})

    def _search_play_count(self, operator, value):
        return self._search_pref("play_count", operator, value)

    @api.depends("pref_ids")
    def _compute_last_play(self):
        for obj in self:
            obj.last_play = obj._get_pref("last_play")

    def _inverse_last_play(self):
        for obj in self:
            obj._set_pref({"last_play": obj.last_play})

    def _search_last_play(self, operator, value):
        return self._search_pref("last_play", operator, value)

    @api.depends("pref_ids")
    def _compute_star(self):
        for obj in self:
            obj.star = obj._get_pref("star")

    def _inverse_star(self):
        for obj in self:
            obj._set_pref({"star": obj.star})

    def _search_star(self, operator, value):
        return self._search_pref("star", operator, value)

    @api.depends("pref_ids")
    def _compute_rating(self):
        for obj in self:
            obj.rating = obj._get_pref("rating")

    def _inverse_rating(self):
        for obj in self:
            obj._set_pref({"rating": obj.rating})

    def _search_rating(self, operator, value):
        return self._search_pref("rating", operator, value)

    @api.depends("pref_ids")
    def _compute_bit_follow(self):
        for obj in self:
            obj.bit_follow = obj._get_pref("bit_follow") or "normal"

    def _inverse_bit_follow(self):
        for obj in self:
            obj._set_pref({"bit_follow": obj.bit_follow})

    def _search_bit_follow(self, operator, value):
        return self._search_pref("bit_follow", operator, value)

    @api.depends("pref_ids")
    def _compute_tag_ids(self):
        self.env.cr.execute("SELECT true FROM oomusic_preference_oomusic_tag_rel LIMIT 1")
        row = self.env.cr.fetchone()
        for obj in self:
            obj.tag_ids = obj._get_pref("tag_ids") if row else False

    def _inverse_tag_ids(self):
        for obj in self:
            obj._set_pref({"tag_ids": [(6, 0, obj.tag_ids.ids)]})

    def _search_tag_ids(self, operator, value):
        return self._search_pref("tag_ids", operator, value)

    def _get_pref(self, field):
        return self.pref_ids[field]

    def _set_pref(self, vals):
        invalidate_cache = False
        for obj in self:
            if not obj.pref_ids:
                vals["res_model_id"] = (
                    self.env["ir.model"].sudo().search([("model", "=", obj._name)], limit=1).id
                )
                vals["res_id"] = obj.id
                vals["res_user_id"] = obj.user_id.id
                self.env["oomusic.preference"].create(vals)
                # In case no preference entry exist and we write on more than one preference field,
                # we create as many preference entry as preference fields. We force cache
                # invalidation to prevent this.
                invalidate_cache = True
            else:
                obj.pref_ids.write(vals)
        if invalidate_cache:
            self.invalidate_cache()

    def _search_pref(self, field, operator, value):
        pref = self.env["oomusic.preference"].search(
            [
                (field, operator, value),
                ("res_model", "=", self._name),
                ("user_id", "=", self.env.uid),
            ]
        )
        return [("id", "in", [p["res_id"] for p in pref.read(["res_id"])])]

    def write(self, vals):
        # When calling write, a `check_access_rule('write')` is performed even if we don't really
        # write on `self`. This is for example the case for the fields defined in
        # `oomusic.preference`.
        # When the library is shared, this triggers an AccessError if the user is not the owner
        # of the object.
        fields = {"play_count", "last_play", "star", "rating", "bit_follow", "tag_ids"}
        new_self = self
        if any([k in fields for k in vals.keys()]):
            self.check_access_rule("read")
            new_self = self.sudo().with_context(default_user_id=self.env.user.id)
        return super(MusicPreferenceMixin, new_self).write(vals)

    def unlink(self):
        """ When removing a record, its preferences should be deleted too. """
        rec_ids = self.ids
        res = super(MusicPreferenceMixin, self).unlink()
        self.env["oomusic.preference"].sudo().search(
            [("res_model", "=", self._name), ("res_id", "in", rec_ids)]
        ).unlink()
        return res
