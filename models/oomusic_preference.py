# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MusicPreference(models.Model):
    _name = 'oomusic.preference'
    _rec_name = 'res_model'
    _order = 'id'
    _description = 'User preference'

    res_model_id = fields.Many2one(
        'ir.model', 'Related Document Model', ondelete='cascade',
        help='Model of the preference resource')
    res_model = fields.Char(
        string='Document Model', related='res_model_id.model', store=True, readonly=True)
    res_id = fields.Integer(
        string='Document', required=True, help='Identifier of the preference object')
    res_user_id = fields.Many2one(
        'res.users', string='Document User', index=True, required=True, ondelete='cascade'
    )
    user_id = fields.Many2one(
        'res.users', string='User', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.user
    )
    play_count = fields.Integer('Play Count', default=0, readonly=True)
    last_play = fields.Datetime('Last Played', index=True, readonly=True)
    in_playlist = fields.Boolean('In Current Playlist')
    star = fields.Selection(
        [('0', 'Normal'), ('1', 'I Like It!')], 'Favorite', default='0')
    rating = fields.Selection(
        [('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
        'Rating', default='0',
    )


class MusicPreferenceMixin(models.AbstractModel):
    _name = 'oomusic.preference.mixin'
    _description = "Download Mixin"

    pref_ids = fields.One2many(
        'oomusic.preference', 'res_id', string='User Preferences',
        domain=lambda self: [('res_model', '=', self._name), ('user_id', '=', self.env.user.id)],
        auto_join=True)

    @api.depends('pref_ids')
    def _compute_play_count(self):
        for obj in self:
            obj.play_count = obj._get_pref('play_count')

    def _inverse_play_count(self):
        for obj in self:
            obj._set_pref({'play_count': obj.play_count})

    def _search_play_count(self, operator, value):
        return self._search_pref('play_count', operator, value)

    @api.depends('pref_ids')
    def _compute_last_play(self):
        for obj in self:
            obj.last_play = obj._get_pref('last_play')

    def _inverse_last_play(self):
        for obj in self:
            obj._set_pref({'last_play': obj.last_play})

    def _search_last_play(self, operator, value):
        return self._search_pref('last_play', operator, value)

    @api.depends('pref_ids')
    def _compute_in_playlist(self):
        for obj in self:
            obj.in_playlist = obj._get_pref('in_playlist')

    def _inverse_in_playlist(self):
        for obj in self:
            obj._set_pref({'in_playlist': obj.in_playlist})

    def _search_in_playlist(self, operator, value):
        return self._search_pref('in_playlist', operator, value)

    @api.depends('pref_ids')
    def _compute_star(self):
        for obj in self:
            obj.star = obj._get_pref('star')

    def _inverse_star(self):
        for obj in self:
            obj._set_pref({'star': obj.star})

    def _search_star(self, operator, value):
        return self._search_pref('star', operator, value)

    @api.depends('pref_ids')
    def _compute_rating(self):
        for obj in self:
            obj.rating = obj._get_pref('rating')

    def _inverse_rating(self):
        for obj in self:
            obj._set_pref({'rating': obj.rating})

    def _search_rating(self, operator, value):
        return self._search_pref('rating', operator, value)

    def _get_pref(self, field):
        return self.pref_ids[field]

    def _set_pref(self, vals):
        invalidate_cache = False
        for obj in self:
            if not obj.pref_ids:
                vals['res_model_id'] = self.env['ir.model'].sudo().search(
                    [('model', '=', obj._name)], limit=1).id
                vals['res_id'] = obj.id
                vals['res_user_id'] = obj.user_id.id
                self.env['oomusic.preference'].create(vals)
                # In case no preference entry exist and we write on more than one preference field,
                # we create as many preference entry as preference fields. We force cache
                # invalidation to prevent this.
                invalidate_cache = True
            else:
                obj.pref_ids.write(vals)
        if invalidate_cache:
            self.invalidate_cache()

    def _search_pref(self, field, operator, value):
        pref = self.env['oomusic.preference'].search([
            (field, operator, value), ('res_model', '=', self._name)
        ])
        return [('id', 'in', pref.mapped('res_id'))]

    def unlink(self):
        """ When removing a record, its preferences should be deleted too. """
        rec_ids = self.ids
        res = super(MusicPreferenceMixin, self).unlink()
        self.env['oomusic.preference'].sudo().search(
            [('res_model', '=', self._name), ('res_id', 'in', rec_ids)]).unlink()
        return res