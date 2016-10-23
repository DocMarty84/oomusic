# -*- coding: utf-8 -*-

import datetime
import json
import time

import requests
from werkzeug.urls import url_fix

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from odoo.tools.safe_eval import safe_eval


class MusicArtist(models.Model):
    _name = 'oomusic.artist'
    _description = 'Music Artist'
    _order = 'name'

    name = fields.Char('Artist', index=True)
    track_ids = fields.One2many('oomusic.track', 'artist_id', string='Tracks')
    album_ids = fields.One2many('oomusic.album', 'artist_id', string='Albums')
    user_id = fields.Many2one(
        'res.users', string='User', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.user
    )

    star = fields.Selection(
        [('0', 'Normal'), ('1', 'I Like It!')], 'Favorite', index=True, default='0')
    rating = fields.Selection(
        [('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
        'Rating', default='0',
    )

    fm_last_update = fields.Datetime('Last Update', default='2000-01-01 00:00:00')
    fm_getinfo_bio = fields.Char('Biography', compute='_compute_fm_getinfo')
    fm_getinfo_bio_cache = fields.Char('Biography')
    fm_getinfo_mbid = fields.Char('MusicBrainz ID', compute='_compute_fm_getinfo')
    fm_getinfo_mbid_cache = fields.Char('MusicBrainz ID')
    fm_gettoptracks = fields.Many2many(
        'oomusic.track', string='Top Tracks', compute='_compute_fm_gettoptracks')
    fm_gettoptracks_cache = fields.Char('Top Tracks')
    fm_getsimilar = fields.Many2many(
        'oomusic.artist', string='Similar Artists', compute='_compute_fm_getsimilar')
    fm_getsimilar_cache = fields.Char('Similar Artists')

    _sql_constraints = [
        ('oomusic_artist_name_uniq', 'unique(name, user_id)', 'Artist name must be unique!'),
    ]

    def _compute_fm_getinfo(self):
        if not self.env.context.get('compute_fields', True):
            return

        # Get LastFM key and cache duration
        ConfigParam = self.env['ir.config_parameter'].sudo()
        fm_key = ConfigParam.get_param('oomusic.lastfm_key')
        fm_cache = int(ConfigParam.get_param('oomusic.lastfm_cache', 14))
        if not fm_key:
            return

        for artist in self:
            fm_last_update = datetime.datetime.strptime(artist.fm_last_update, DATETIME_FORMAT)
            if artist.fm_getinfo_bio_cache\
                    and (fm_last_update - datetime.datetime.utcnow()).days < fm_cache:
                artist.fm_getinfo_bio = artist.fm_getinfo_bio_cache
                artist.fm_getinfo_mbid = artist.fm_getinfo_mbid_cache
                continue

            fm_key = self.env['ir.config_parameter'].sudo().get_param('oomusic.lastfm_key')
            getinfo_url = url_fix(
                'https://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist='\
                + artist.name + '&api_key=' + fm_key + '&format=json'
            )
            try:
                r = requests.get(getinfo_url, timeout=3.0)
                if r.status_code == 200:
                    r_json = json.loads(r.content)
                    artist.fm_getinfo_bio =\
                        r_json['artist']['bio']['content'].replace('\n', '<br/>')\
                        or _('Biography not found')
                    artist.fm_getinfo_mbid = r_json['artist']['mbid']

            except:
                artist.fm_getinfo_bio = _('Biography not found')

            # Save in cache
            new_cr = self.pool.cursor()
            new_self = self.with_env(self.env(cr=new_cr))
            new_self.env['oomusic.artist'].browse(artist.id).sudo().write({
                'fm_getinfo_bio_cache': artist.fm_getinfo_bio,
                'fm_getinfo_mbid_cache': artist.fm_getinfo_mbid,
                'fm_last_update': fields.Datetime.now(),
            })
            new_self.env.cr.commit()
            new_self.env.cr.close()

    def _compute_fm_gettoptracks(self):
        if not self.env.context.get('compute_fields', True):
            return

        # Get LastFM key and cache duration
        ConfigParam = self.env['ir.config_parameter'].sudo()
        fm_key = ConfigParam.get_param('oomusic.lastfm_key')
        fm_cache = int(ConfigParam.get_param('oomusic.lastfm_cache', 14))
        if not fm_key:
            return

        for artist in self:
            fm_last_update = datetime.datetime.strptime(artist.fm_last_update, DATETIME_FORMAT)
            if artist.fm_gettoptracks_cache\
                    and artist.fm_gettoptracks_cache != "[]"\
                    and (fm_last_update - datetime.datetime.utcnow()).days < fm_cache:
                top_tracks = safe_eval(artist.fm_gettoptracks_cache or "[]")
                artist.fm_gettoptracks = self.env['oomusic.track'].browse(top_tracks).exists().ids
                continue

            gettoptracks_url = url_fix(
                'https://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&artist='\
                + artist.name + '&api_key=' + fm_key + '&format=json'
            )
            try:
                r = requests.get(gettoptracks_url, timeout=3.0)
                if r.status_code == 200:
                    r_json = json.loads(r.content)
                    track_cache = {
                        ''.join(c.lower() for c in t.name if c.isalnum()): t.id
                        for t in artist.track_ids
                    }
                    fm_gettoptracks = []
                    for track in r_json['toptracks']['track']:
                        track_name = ''.join(c.lower() for c in track['name'] if c.isalnum())
                        if track_name in track_cache.keys():
                            fm_gettoptracks.append(track_cache[track_name])
                            if len(fm_gettoptracks) > 9:
                                break
                    artist.fm_gettoptracks = fm_gettoptracks

            except:
                artist.fm_gettoptracks = []

            # Save in cache
            new_cr = self.pool.cursor()
            new_self = self.with_env(self.env(cr=new_cr))
            new_self.env['oomusic.artist'].browse(artist.id).sudo().write({
                'fm_gettoptracks_cache': str(artist.fm_gettoptracks.ids),
                'fm_last_update': fields.Datetime.now(),
            })
            new_self.env.cr.commit()
            new_self.env.cr.close()

    def _compute_fm_getsimilar(self):
        if not self.env.context.get('compute_fields', True):
            return

        # Get LastFM key and cache duration
        ConfigParam = self.env['ir.config_parameter'].sudo()
        fm_key = ConfigParam.get_param('oomusic.lastfm_key')
        fm_cache = int(ConfigParam.get_param('oomusic.lastfm_cache', 14))
        if not fm_key:
            return

        for artist in self:
            fm_last_update = datetime.datetime.strptime(artist.fm_last_update, DATETIME_FORMAT)
            if artist.fm_getsimilar_cache\
                    and artist.fm_getsimilar_cache != "[]"\
                    and (fm_last_update - datetime.datetime.utcnow()).days < fm_cache:
                s_artists = safe_eval(artist.fm_getsimilar_cache or "[]")
                artist.fm_getsimilar = self.env['oomusic.artist'].browse(s_artists).exists().ids
                continue

            getsimilar_url = url_fix(
                'https://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&artist='\
                + artist.name + '&api_key=' + fm_key + '&format=json'
            )
            try:
                r = requests.get(getsimilar_url, timeout=3.0)
                if r.status_code == 200:
                    r_json = json.loads(r.content)
                    s_artist_cache = {
                        ''.join(c.lower() for c in a.name if c.isalnum()): a.id
                        for a in self.env['oomusic.artist'].search([('user_id', '=', artist.user_id.id)])
                    }
                    fm_getsimilar = []
                    for s_artist in r_json['similarartists']['artist']:
                        s_artist_name = ''.join(c.lower() for c in s_artist['name'] if c.isalnum())
                        if s_artist_name in s_artist_cache.keys():
                            fm_getsimilar.append(s_artist_cache[s_artist_name])
                            if len(fm_getsimilar) > 4:
                                break
                    artist.fm_getsimilar = fm_getsimilar

            except:
                artist.fm_getsimilar = []

            # Save in cache
            new_cr = self.pool.cursor()
            new_self = self.with_env(self.env(cr=new_cr))
            new_self.env['oomusic.artist'].browse(artist.id).sudo().write({
                'fm_getsimilar_cache': str(artist.fm_getsimilar.ids),
                'fm_last_update': fields.Datetime.now(),
            })
            new_self.env.cr.commit()
            new_self.env.cr.close()

    @api.multi
    def action_add_to_playlist(self):
        Playlist = self.env['oomusic.playlist'].search([('current', '=', True)], limit=1)
        if not Playlist:
            raise UserError(_('No current playlist found!'))
        for artist in self:
            Playlist._add_tracks(artist.track_ids)

    @api.model
    def cron_build_lastfm_cache(self):
        fm_cache = int(self.env['ir.config_parameter'].sudo().get_param('oomusic.lastfm_cache', 14))
        dt_limit = datetime.datetime.utcnow() - datetime.timedelta(fm_cache)
        artists = self.search(
            [('fm_last_update', '<', dt_limit.strftime(DATETIME_FORMAT))], limit=200
        )
        for artist in artists:
            artist._compute_fm_getinfo()
            artist._compute_fm_gettoptracks()
            artist._compute_fm_getsimilar()
            time.sleep(1.0)
