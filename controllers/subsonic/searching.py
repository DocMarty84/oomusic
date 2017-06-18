# -*- coding: utf-8 -*-

import os

from lxml import etree

from odoo import http
from odoo.http import request
from common import SubsonicREST


class MusicSubsonicSearching(http.Controller):
    @http.route(['/rest/search.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def search(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        artists = albums = tracks = []

        s_artist = kwargs.get('artist', '')
        s_album = kwargs.get('album', '')
        s_title = kwargs.get('title', '')
        s_any = kwargs.get('any', '')

        size = min(int(kwargs.get('count', 20)), 500)
        offset = int(kwargs.get('offset', 0))
        newerThan = int(kwargs.get('newerThan', 0))/1000

        domain = [('last_modification', '>=', newerThan)]

        if s_artist or s_any:
            domain_artist = domain
            if s_any:
                domain_artist += [('path', 'ilike', s_any)]
            if s_artist:
                domain_artist += [('path', 'ilike', s_artist)]
            artists = request.env['oomusic.folder'].search(domain_artist)\
                .filtered(lambda r: len(r.track_ids) == 0)

            if s_any:
                artists = artists\
                    .filtered(lambda r: s_any.lower() in os.path.basename(r.path).lower())
            if s_artist:
                artists = artists\
                    .filtered(lambda r: s_artist.lower() in os.path.basename(r.path).lower())

        if s_album or s_any:
            domain_album = domain
            if s_any:
                domain_album += [('path', 'ilike', s_any)]
            if s_album:
                domain_album += [('path', 'ilike', s_album)]
            albums = request.env['oomusic.folder'].search(domain_album)\
                .filtered(lambda r: len(r.track_ids) != 0)

            if s_any:
                albums = albums\
                    .filtered(lambda r: s_any.lower() in os.path.basename(r.path).lower())
            if s_album:
                albums = albums\
                    .filtered(lambda r: s_album.lower() in os.path.basename(r.path).lower())

        if s_title or s_any:
            domain_title = domain
            if s_any:
                domain_title += [('name', 'ilike', s_any)]
            if s_title:
                domain_title += [('name', 'ilike', s_title)]
            tracks = request.env['oomusic.track'].search(domain_title)

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_search = rest.make_SearchResult(
            offset=str(offset), totalHits=str(len(artists) + len(albums) + len(tracks)))
        root.append(xml_search)

        if artists:
            min_val = min(offset, len(artists))
            max_val = min_val + size
            for artist in artists[min_val:max_val]:
                xml_artist = rest.make_Artist(artist)
                xml_search.append(xml_artist)

        if albums:
            min_val = min(offset, len(albums))
            max_val = min_val + size
            for album in albums[min_val:max_val]:
                xml_album = rest.make_Child_folder(album, tag_name='match')
                xml_search.append(xml_album)

        if tracks:
            min_val = min(offset, len(tracks))
            max_val = min_val + size
            for track in tracks[min_val:max_val]:
                xml_song = rest.make_Child_track(track, tag_name='match')
                xml_search.append(xml_song)

        return rest.make_response(root)

    @http.route(['/rest/search2.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def search2(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        query = kwargs.get('query')
        if not query:
            return rest.make_error(
                code='10', message='Required str parameter "query" is not present')

        artistCount = min(int(kwargs.get('artistCount', 20)), 500)
        artistOffset = int(kwargs.get('artistOffset', 0))
        albumCount = min(int(kwargs.get('albumCount', 20)), 500)
        albumOffset = int(kwargs.get('albumOffset', 0))
        songCount = min(int(kwargs.get('songCount', 20)), 500)
        songOffset = int(kwargs.get('songOffset', 0))

        folderId = kwargs.get('musicFolderId')
        if folderId:
            folder = request.env['oomusic.folder'].browse([int(folderId)])
            if not folder.exists():
                return rest.make_error(code='70', message='Folder not found')

        domain = [('folder_id', 'child_of', int(folderId))] if folderId else []
        folders = request.env['oomusic.folder'].search(domain + [('path', 'ilike', query)])\
            .filtered(lambda r: query.lower() in os.path.basename(r.path).lower())
        artists = folders.filtered(lambda r: len(r.track_ids) == 0)
        albums = folders.filtered(lambda r: len(r.track_ids) != 0)
        tracks = request.env['oomusic.track'].search(domain + [('name', 'ilike', query)])

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_search = rest.make_SearchResult2()
        root.append(xml_search)

        if artists:
            min_val = min(artistOffset, len(artists))
            max_val = min_val + artistCount
            for artist in artists[min_val:max_val]:
                xml_artist = rest.make_Artist(artist)
                xml_search.append(xml_artist)

        if albums:
            min_val = min(albumOffset, len(albums))
            max_val = min_val + albumCount
            for album in albums[min_val:max_val]:
                xml_album = rest.make_Child_folder(album, tag_name='album')
                xml_search.append(xml_album)

        if tracks:
            min_val = min(songOffset, len(tracks))
            max_val = min_val + songCount
            for track in tracks[min_val:max_val]:
                xml_song = rest.make_Child_track(track, tag_name='song')
                xml_search.append(xml_song)

        return rest.make_response(root)

    @http.route(['/rest/search3.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def search3(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        query = kwargs.get('query')
        if not query:
            return rest.make_error(
                code='10', message='Required str parameter "query" is not present')

        artistCount = min(int(kwargs.get('artistCount', 20)), 500)
        artistOffset = int(kwargs.get('artistOffset', 0))
        albumCount = min(int(kwargs.get('albumCount', 20)), 500)
        albumOffset = int(kwargs.get('albumOffset', 0))
        songCount = min(int(kwargs.get('songCount', 20)), 500)
        songOffset = int(kwargs.get('songOffset', 0))

        folderId = kwargs.get('musicFolderId')
        if folderId:
            folder = request.env['oomusic.folder'].browse([int(folderId)])
            if not folder.exists():
                return rest.make_error(code='70', message='Folder not found')

        domain = [('folder_id', 'child_of', int(folderId))] if folderId else []
        artists = request.env['oomusic.artist'].search(domain + [('name', 'ilike', query)])
        albums = request.env['oomusic.album'].search(domain + [('name', 'ilike', query)])
        tracks = request.env['oomusic.track'].search(domain + [('name', 'ilike', query)])

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_search = rest.make_SearchResult2(tag_name='searchResult3')
        root.append(xml_search)

        if artists:
            min_val = min(artistOffset, len(artists))
            max_val = min_val + artistCount
            for artist in artists[min_val:max_val]:
                xml_artist = rest.make_ArtistID3(artist)
                xml_search.append(xml_artist)

        if albums:
            min_val = min(albumOffset, len(albums))
            max_val = min_val + albumCount
            for album in albums[min_val:max_val]:
                xml_album = rest.make_AlbumID3(album)
                xml_search.append(xml_album)

        if tracks:
            min_val = min(songOffset, len(tracks))
            max_val = min_val + songCount
            for track in tracks[min_val:max_val]:
                xml_song = rest.make_Child_track(track, tag_name='song')
                xml_search.append(xml_song)

        return rest.make_response(root)
