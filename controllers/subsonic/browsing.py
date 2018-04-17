# -*- coding: utf-8 -*-

import logging
from lxml import etree

from odoo import http
from odoo.http import request
from .common import SubsonicREST

_logger = logging.getLogger(__name__)


class MusicSubsonicBrowsing(http.Controller):
    @http.route(['/rest/getMusicFolders.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getMusicFolders(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_music_folders = rest.make_MusicFolders()
        root.append(xml_music_folders)

        for folder in request.env['oomusic.folder'].search([('root', '=', True)]):
            xml_music_folder = rest.make_MusicFolder(folder)
            xml_music_folders.append(xml_music_folder)

        return rest.make_response(root)

    @http.route(['/rest/getIndexes.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getIndexes(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        ifModifiedSince = kwargs.get('ifModifiedSince')
        if ifModifiedSince:
            try:
                ifModifiedSince = int(ifModifiedSince) // 1000
            except ValueError:
                _logger.warn(
                    'Could not convert param "ifModifiedSince" %s to integer', ifModifiedSince)
                return rest.make_error(code='0', message='Invalid timestamp')

        musicFolderId = kwargs.get('musicFolderId')
        if musicFolderId is None:
            folder = request.env['oomusic.folder'].search([('root', '=', True)], limit=1)
        else:
            folder = request.env['oomusic.folder'].browse([int(musicFolderId)])
            if not folder.exists():
                return rest.make_error(code='70', message='Folder not found')

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_indexes = rest.make_Indexes(folder)
        root.append(xml_indexes)

        if ifModifiedSince is not None and folder.last_modification < ifModifiedSince:
            return rest.make_response(root)

        # Build indexes
        indexes_dict = rest.build_dict_indexes_folder(folder)

        # List of folders
        for k, v in sorted(indexes_dict.items()):
            xml_index = rest.make_Index(k)
            xml_indexes.append(xml_index)
            for child in v:
                xml_data = rest.make_Artist(child)
                xml_index.append(xml_data)

        # List of tracks
        for track in folder.track_ids:
            xml_data = rest.make_Child_track(track)
            xml_indexes.append(xml_data)

        return rest.make_response(root)

    @http.route(['/rest/getMusicDirectory.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getMusicDirectory(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        folderId = kwargs.get('id')
        if folderId:
            folder = request.env['oomusic.folder'].browse([int(folderId)])
            if not folder.exists():
                return rest.make_error(code='70', message='Folder not found')
        else:
            return rest.make_error(code='10', message='Required int parameter "id" is not present')

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_directory = rest.make_Directory(folder)
        root.append(xml_directory)

        # List of folders
        for child in folder.child_ids:
            xml_data = rest.make_Child_folder(child)
            xml_directory.append(xml_data)

        # List of tracks
        for track in folder.track_ids:
            xml_data = rest.make_Child_track(track)
            xml_directory.append(xml_data)

        return rest.make_response(root)

    @http.route(['/rest/getGenres.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getGenres(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_genres = rest.make_Genres()
        root.append(xml_genres)

        return rest.make_response(root)

    @http.route(['/rest/getArtists.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getArtists(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_artists = rest.make_ArtistsID3()
        root.append(xml_artists)

        musicFolderId = kwargs.get('musicFolderId')
        if musicFolderId:
            artists = request.env['oomusic.track'].search([
                ('folder_id', 'child_of', int(musicFolderId))
            ]).mapped('artist_id')
        else:
            artists = request.env['oomusic.artist'].search([])

        # Build indexes
        indexes_dict = rest.build_dict_indexes_artists(artists)

        # List of artists
        for k, v in sorted(indexes_dict.items()):
            xml_index = rest.make_IndexID3(k)
            xml_artists.append(xml_index)
            for artist in v:
                xml_artist = rest.make_ArtistID3(artist)
                xml_index.append(xml_artist)

        return rest.make_response(root)

    @http.route(['/rest/getArtist.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getArtist(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        artistId = kwargs.get('id')
        if artistId:
            artist = request.env['oomusic.artist'].browse([int(artistId)])
            if not artist.exists():
                return rest.make_error(code='70', message='Artist not found')
        else:
            return rest.make_error(code='10', message='Required int parameter "id" is not present')

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_artist = rest.make_ArtistID3(artist)
        root.append(xml_artist)

        for album in artist.album_ids:
            xml_album = rest.make_AlbumID3(album)
            xml_artist.append(xml_album)

        return rest.make_response(root)

    @http.route(['/rest/getAlbum.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getAlbum(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        albumId = kwargs.get('id')
        if albumId:
            album = request.env['oomusic.album'].browse([int(albumId)])
            if not album.exists():
                return rest.make_error(code='70', message='Album not found')
        else:
            return rest.make_error(code='10', message='Required int parameter "id" is not present')

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_album = rest.make_AlbumID3(album)
        root.append(xml_album)

        for track in album.track_ids:
            xml_song = rest.make_Child_track(track, tag_name='song')
            xml_album.append(xml_song)

        return rest.make_response(root)

    @http.route(['/rest/getSong.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getSong(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        songId = kwargs.get('id')
        if songId:
            track = request.env['oomusic.track'].browse([int(songId)])
            if not track.exists():
                return rest.make_error(code='70', message='Song not found')
        else:
            return rest.make_error(code='10', message='Required int parameter "id" is not present')

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_song = rest.make_Child_track(track, tag_name='song')
        root.append(xml_song)

        return rest.make_response(root)

    @http.route(['/rest/getVideos.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getVideos(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_videos = rest.make_Videos()
        root.append(xml_videos)

        return rest.make_response(root)

    @http.route(['/rest/getVideoInfo.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getVideoInfo(self, **kwargs):
        # TODO: support video infos
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        return request.make_error(code='30', message='Videos are not supported yet')

    @http.route(['/rest/getArtistInfo.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getArtistInfo(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        folderId = kwargs.get('id')
        if folderId:
            folder = request.env['oomusic.folder'].browse([int(folderId)])
            if not folder.exists():
                return rest.make_error(code='70', message='Folder not found')
        else:
            return rest.make_error(code='10', message='Required int parameter "id" is not present')

        count = int(kwargs.get('count', 20))
        if kwargs.get('includeNotPresent'):
            includeNotPresent = True if kwargs.get('includeNotPresent') == 'true' else False
        else:
            includeNotPresent = False

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_artist_info = rest.make_ArtistInfo(
            folder, count=count, includeNotPresent=includeNotPresent
        )
        root.append(xml_artist_info)

        return rest.make_response(root)

    @http.route(['/rest/getArtistInfo2.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getArtistInfo2(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        artistId = kwargs.get('id')
        if artistId:
            artist = request.env['oomusic.artist'].browse([int(artistId)])
            if not artist.exists():
                return rest.make_error(code='70', message='Artist not found')
        else:
            return rest.make_error(code='10', message='Required int parameter "id" is not present')

        count = int(kwargs.get('count', 20))
        if kwargs.get('includeNotPresent'):
            includeNotPresent = True if kwargs.get('includeNotPresent') == 'true' else False
        else:
            includeNotPresent = False

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_artist_info = rest.make_ArtistInfo2(
            artist, count=count, includeNotPresent=includeNotPresent
        )
        root.append(xml_artist_info)

        return rest.make_response(root)

    @http.route(['/rest/getAlbumInfo.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getAlbumInfo(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        folderId = kwargs.get('id')
        if folderId:
            folder = request.env['oomusic.folder'].browse([int(folderId)])
            if not folder.exists():
                return rest.make_error(code='70', message='Folder not found')
        else:
            return rest.make_error(code='10', message='Required int parameter "id" is not present')

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_album_info = rest.make_AlbumInfo(folder)
        root.append(xml_album_info)

        return rest.make_response(root)

    @http.route(['/rest/getAlbumInfo2.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getAlbumInfo2(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        albumId = kwargs.get('id')
        if albumId:
            album = request.env['oomusic.album'].browse([int(albumId)])
            if not album.exists():
                return rest.make_error(code='70', message='Album not found')
        else:
            return rest.make_error(code='10', message='Required int parameter "id" is not present')

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_album_info = rest.make_AlbumInfo2(album)
        root.append(xml_album_info)

        return rest.make_response(root)

    @http.route(['/rest/getSimilarSongs.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getSimilarSongs(self, **kwargs):
        return self.getSimilarSongs2(**dict(kwargs, tag_name='similarSongs'))

    @http.route(['/rest/getSimilarSongs2.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getSimilarSongs2(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        songId = kwargs.get('id')
        if songId:
            track = request.env['oomusic.track'].browse([int(songId)])
            if not track.exists():
                return rest.make_error(code='70', message='Song not found')
        else:
            return rest.make_error(code='10', message='Required int parameter "id" is not present')

        count = int(kwargs.get('count', 50))
        tag_name = kwargs.get('tag_name', 'similarSongs2')

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_song_info = rest.make_SimilarSongs2(track, count=count, tag_name=tag_name)
        root.append(xml_song_info)

        return rest.make_response(root)

    @http.route(['/rest/getTopSongs.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getTopSongs(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        artist_name = kwargs.get('artist')
        if not artist_name:
            return rest.make_error(
                code='10', message='Required string parameter "artist" is not present'
            )

        count = int(kwargs.get('count', 50))

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_song_info = rest.make_TopSongs(artist_name, count=count)
        root.append(xml_song_info)

        return rest.make_response(root)
