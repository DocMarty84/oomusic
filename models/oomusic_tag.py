# -*- coding: utf-8 -*-

from odoo import fields, models


class MusicTag(models.Model):
    _name = "oomusic.tag"
    _description = "Custom Tags"

    name = fields.Char(required=True)
    color = fields.Integer(string="Color Index")

    _sql_constraints = [("name_uniq", "unique (name)", "Tag name already exists!")]
