# -*- coding: utf-8 -*-

from odoo import fields, models


class MusicFormat(models.Model):
    _name = 'oomusic.format'
    _description = 'Music Format'
    _order = 'name'

    name = fields.Char('Format', required=True, index=True)
    mimetype = fields.Char('Mimetype', required=True)

    _sql_constraints = [
        ('oomusic_format_name_uniq', 'unique(name)', 'Format name must be unique!'),
    ]
