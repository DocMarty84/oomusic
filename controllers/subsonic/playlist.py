# -*- coding: utf-8 -*-

from lxml import etree

from odoo import http
from odoo.http import request
from common import SubsonicREST, API_VERSION_LIST

class MusicSubsonicPlaylist(http.Controller):
    @http.route(['/rest/getPlaylists.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getPlaylists(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_playlists = rest.make_Playlists()
        root.append(xml_playlists)

        for playlist in request.env['oomusic.playlist'].search([]):
            xml_playlist = rest.make_Playlist(playlist)
            xml_playlists.append(xml_playlist)

        return rest.make_response(root)

    @http.route(['/rest/getPlaylist.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getPlaylist(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        playlistId = kwargs.get('id')
        if playlistId:
            playlist = request.env['oomusic.playlist'].browse([int(playlistId)])
            if not playlist.exists():
                return rest.make_error(code='70', message='Playlist not found')
        else:
            return rest.make_error(code='10', message='Required int parameter "id" is not present')

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_playlist = rest.make_Playlist(playlist)
        root.append(xml_playlist)

        for playlist_line in playlist.playlist_line_ids:
            xml_playlist_line = rest.make_Child_track(playlist_line.track_id, tag_name='entry')
            xml_playlist.append(xml_playlist_line)

        return rest.make_response(root)

    @http.route(['/rest/createPlaylist.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def createPlaylist(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        PlaylistObj = request.env['oomusic.playlist']
        mode = 'create'

        playlistId = kwargs.get('id')
        if playlistId:
            playlist = PlaylistObj.browse([int(playlistId)])
            if playlist.exists():
                mode = 'update'

        name = kwargs.get('name')
        if mode == 'mode' and not name:
            return rest.make_error(
                code='10', message='Required str parameter "name" is not present')

        songId = kwargs.get('songId')
        if songId:
            track = request.env['oomusic.track'].browse([int(songId)])
            if not track.exists():
                return rest.make_error(code='70', message='Song not found')

        if mode == 'create':
            playlist = PlaylistObj.create({'name': name})

        if playlist:
            playlist._add_tracks(track)

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        if API_VERSION_LIST[rest.version_client] >= API_VERSION_LIST['1.14.0']:
            xml_playlist = rest.make_Playlist(playlist)
            root.append(xml_playlist)

            for playlist_line in playlist.playlist_line_ids:
                xml_playlist_line = rest.make_Child_track(playlist_line.track_id, tag_name='entry')
                xml_playlist.append(xml_playlist_line)

        return rest.make_response(root)

    @http.route(['/rest/updatePlaylist.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def updatePlaylist(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        PlaylistObj = request.env['oomusic.playlist']

        playlistId = kwargs.get('playlistId')
        if playlistId:
            playlist = PlaylistObj.browse([int(playlistId)])
            if not playlist.exists():
                return rest.make_error(code='70', message='Playlist not found')

        name = kwargs.get('name')
        comment = kwargs.get('comment')
        public = kwargs.get('public')

        songIdToAdd = kwargs.get('songIdToAdd')
        if songIdToAdd:
            track_add = request.env['oomusic.track'].browse([int(songIdToAdd)])
            if not track_add.exists():
                return rest.make_error(code='70', message='Song not found')

        songIndexToRemove = kwargs.get('songIndexToRemove')
        if songIndexToRemove:
            track_remove = request.env['oomusic.track'].browse([int(songIndexToRemove)])
            if not track_remove.exists():
                return rest.make_error(code='70', message='Song not found')

        vals = {}
        if name:
            vals['name'] = name
        if comment:
            vals['comment'] = comment
        if public:
            vals['public'] = True if public == 'true' else False
        playlist.write(vals)
        if songIdToAdd:
            playlist._add_tracks(track_add)
        if songIndexToRemove:
            line_remove = playlist.mapped('playlist_line_ids')\
                .filtered(lambda r: r.track_id == track_remove)
            line_remove.unlink()

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)

        return rest.make_response(root)

    @http.route(['/rest/deletePlaylist.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def deletePlaylist(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        PlaylistObj = request.env['oomusic.playlist']

        playlistId = kwargs.get('id')
        if playlistId:
            playlist = PlaylistObj.browse([int(playlistId)])
            if not playlist.exists():
                return rest.make_error(code='70', message='Playlist not found')
        else:
            return rest.make_error(code='10', message='Required int parameter "id" is not present')

        playlist.unlink()

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)

        return rest.make_response(root)
