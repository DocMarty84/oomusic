# -*- coding: utf-8 -*-

import base64
import json
import logging
import urllib.request

from odoo import fields, models, api, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MusicArtist(models.Model):
    _name = 'oomusic.artist'
    _description = 'Music Artist'
    _order = 'name'
    _inherit = ['oomusic.download.mixin']

    name = fields.Char('Artist', index=True)
    track_ids = fields.One2many('oomusic.track', 'artist_id', string='Tracks', readonly=True)
    album_ids = fields.One2many('oomusic.album', 'artist_id', string='Albums', readonly=True)
    user_id = fields.Many2one(
        'res.users', string='User', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.user
    )

    star = fields.Selection(
        [('0', 'Normal'), ('1', 'I Like It!')], 'Favorite', default='0')
    rating = fields.Selection(
        [('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
        'Rating', default='0',
    )

    fm_image = fields.Binary(
        'Image', compute='_compute_fm_image',
        help='Image of the artist, obtained thanks to LastFM.')
    fm_image_cache = fields.Binary(
        'Image', attachment=True,
        help='Image of the artist, obtained thanks to LastFM.')
    fm_getinfo_bio = fields.Char('Biography', compute='_compute_fm_getinfo')
    fm_gettoptracks_track_ids = fields.Many2many(
        'oomusic.track', string='Top Tracks', compute='_compute_fm_gettoptracks')
    fm_getsimilar_artist_ids = fields.Many2many(
        'oomusic.artist', string='Similar Artists', compute='_compute_fm_getsimilar')

    _sql_constraints = [
        ('oomusic_artist_name_uniq', 'unique(name, user_id)', 'Artist name must be unique!'),
    ]

    @api.depends('name')
    def _compute_fm_image(self):
        for artist in self:
            if artist.fm_image_cache and not self.env.context.get('build_cache'):
                artist.fm_image = artist.fm_image_cache
                continue

            resized_images = {'image_medium': False}
            req_json = artist._lastfm_artist_getinfo()
            try:
                _logger.debug("Retrieving image for artist %s...", artist.name)
                for image in req_json['artist']['image']:
                    if image['size'] == 'large' and image['#text']:
                        image_content = urllib.request.urlopen(image['#text'], timeout=5).read()
                        resized_images = tools.image_get_resized_images(
                            base64.b64encode(image_content),
                            return_big=False, return_medium=True, return_small=False)
                        break
            except KeyError:
                _logger.info('No image found for artist "%s" (id: %s)', artist.name, artist.id)

            # Avoid doing a write is nothing has to be done
            if not resized_images['image_medium'] and not artist.fm_image_cache:
                _logger.info('No image found for artist "%s" (id: %s)', artist.name, artist.id)
                continue

            artist.fm_image = resized_images['image_medium']

            # Save in cache
            with self.pool.cursor() as cr:
                new_self = self.with_env(self.env(cr=cr))
                new_self.env['oomusic.artist'].browse(artist.id).sudo().write({
                    'fm_image_cache': resized_images['image_medium'],
                })

    def _compute_fm_getinfo(self):
        for artist in self:
            req_json = artist._lastfm_artist_getinfo()
            try:
                artist.fm_getinfo_bio = req_json['artist']['bio']['summary'].replace('\n', '<br/>')
            except KeyError:
                artist.fm_getinfo_bio = _('Biography not found')
                _logger.info('Biography not found for artist "%s" (id: %s)', artist.name, artist.id)

    def _compute_fm_gettoptracks(self):
        # Create a global cache dict for all artists to avoid multiple search calls.
        tracks = self.env['oomusic.track'].search_read(
            [('artist_id', 'in', self.ids)],
            ['id', 'name', 'artist_id'])
        tracks = {(t['artist_id'][0], t['name'].lower()): t['id'] for t in tracks}

        for artist in self:
            req_json = artist._lastfm_artist_gettoptracks()
            try:
                t_tracks = [
                    tracks[(artist.id, t['name'].lower())]
                    for t in req_json['toptracks']['track']
                    if (artist.id, t['name'].lower()) in tracks
                ]
                artist.fm_gettoptracks_track_ids = t_tracks[:10]
            except KeyError:
                _logger.info(
                    'Top tracks not found for artist "%s" (id: %s)', artist.name, artist.id)

    def _compute_fm_getsimilar(self):
        for artist in self:
            req_json = artist._lastfm_artist_getsimilar()
            try:
                s_artists = self.env['oomusic.artist']
                for s_artist in req_json['similarartists']['artist']:
                    s_artists |= self.env['oomusic.artist'].search([
                        ('name', '=ilike', s_artist['name']),
                    ], limit=1)
                    if len(s_artists) > 4:
                        break
                artist.fm_getsimilar_artist_ids = s_artists.ids
            except KeyError:
                _logger.info(
                    'Similar artists not found for artist "%s" (id: %s)', artist.name, artist.id)

    @api.multi
    def action_add_to_playlist(self):
        playlist = self.env['oomusic.playlist'].search([('current', '=', True)], limit=1)
        if not playlist:
            raise UserError(_('No current playlist found!'))
        if self.env.context.get('purge'):
            playlist.action_purge()
        for artist in self:
            playlist._add_tracks(artist.track_ids)

    @api.model
    def cron_build_image_cache(self):
        artists = self.search([]).with_context(build_cache=True, prefetch_fields=False)
        step = 50
        for i in range(0, len(artists), step):
            artist = artists[i:i+step]
            artist._compute_fm_image()
            self.invalidate_cache()

    def _lastfm_artist_getinfo(self):
        self.ensure_one()
        url = 'https://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist=' + self.name
        return json.loads(self.env['oomusic.lastfm'].get_query(url))

    def _lastfm_artist_getsimilar(self):
        self.ensure_one()
        url = 'https://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&artist=' + self.name
        return json.loads(self.env['oomusic.lastfm'].get_query(url))

    def _lastfm_artist_gettoptracks(self):
        self.ensure_one()
        url = 'https://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&artist=' + self.name
        return json.loads(self.env['oomusic.lastfm'].get_query(url))
