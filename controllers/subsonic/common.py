# -*- coding: utf-8 -*-

import binascii
import hashlib
import logging
import mimetypes
import os
from pprint import pformat

from collections import OrderedDict
from lxml import etree

from . import xml2json
from odoo.exceptions import AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)
API_VERSION_LIST = {
    '1.16.0': 17,
    '1.15.0': 16,
    '1.14.0': 15,
    '1.13.0': 14,
    '1.12.0': 13,
    '1.11.0': 12,
    '1.10.2': 11,
    '1.9.0': 10,
    '1.8.0': 9,
    '1.7.0': 8,
    '1.6.0': 7,
    '1.5.0': 6,
    '1.4.0': 5,
    '1.3.0': 4,
    '1.2.0': 3,
    '1.1.1': 2,
    '1.1.0': 1,
    '1.0.0': 0,
}
API_ERROR_LIST = {
    '0': 'A generic error.',
    '10': 'Required parameter is missing.',
    '20': 'Incompatible Subsonic REST protocol version. Client must upgrade.',
    '30': 'Incompatible Subsonic REST protocol version. Server must upgrade.',
    '40': 'Wrong username or password.',
    '41': 'Token authentication not supported for LDAP users.',
    '50': 'User is not authorized for the given operation.',
    '60': 'The trial period for the Subsonic server is over. Please upgrade to Subsonic Premium.',
    '70': 'The requested data was not found.',
}
IGNORED_ARTICLES = ['The', 'El', 'La', 'Los', 'Las', 'Le', 'Les']


class SubsonicREST():
    def __init__(self, args):
        self.login = args.get('u', '')
        self.password = args.get('p', '')
        self.token = args.get('t', '')
        self.salt = args.get('s', '')
        self.version_client = args.get('v', '')
        self.client = args.get('c', '')
        self.format = args.get('f', 'xml')
        self.callback = args.get('callback', '')

        self.version_server = '1.12.0' if 'password_crypt' in request.env['res.users'] else '1.16.0'

    def make_response(self, root):
        if self.format == 'json':
            json_root = xml2json.xml2json(etree.tostring(root))
            return request.make_response(json_root, headers=[
                ('Content-Type', 'application/json; charset=UTF-8'),
                ('Content-Length', len(json_root)),
                ('Access-Control-Allow-Origin', '*'),
            ])
        elif self.format == 'jsonp':
            json_root = xml2json.xml2json(etree.tostring(root))
            json_root = self.callback + '(' + json_root + ');'
            return request.make_response(json_root, headers=[
                ('Content-Type', 'text/javascript; charset=UTF-8'),
                ('Content-Length', len(json_root)),
                ('Access-Control-Allow-Origin', '*'),
            ])
        else:
            response = b'<?xml version="1.0" encoding="UTF-8"?>\n'\
                + etree.tostring(root, encoding='UTF-8', pretty_print=True)
            return request.make_response(response)

    def make_error(self, code='0', message=''):
        root = etree.Element('subsonic-response', status='failed', version=self.version_server)
        etree.SubElement(
            root, 'error', code=code, message=message or API_ERROR_LIST[code]
        )
        return self.make_response(root)

    def check_login(self):
        uid = False
        if self.password:
            if self.password.startswith('enc:'):
                password = binascii.unhexlify(self.password[4:])
            else:
                password = self.password
            uid = request.session.authenticate(request.session.db, self.login, password)

        elif self.token and self.salt:
            request.env.cr.execute('''
                SELECT password FROM res_users
                WHERE login=%s
                    AND active
                    AND password IS NOT NULL
                    AND password != ''
            ''', (self.login,))
            if request.env.cr.rowcount:
                password = request.env.cr.fetchone()[0]
                if hashlib.md5((password + self.salt).encode('utf-8')).hexdigest() == self.token:
                    uid = request.session.authenticate(request.session.db, self.login, password)
            else:
                return False, self.make_error('30')

        if uid:
            root = etree.Element('subsonic-response', status='ok', version=self.version_server)
            return True, self.make_response(root)
        else:
            _logger.info("Subsonic login failed for db:%s login:%s", request.session.db, self.login)
            return False, self.make_error('40')

    def build_dict_indexes_folder(self, folder):
        indexes_dict = {}
        num_list = [str(x) for x in range(10)]
        for child in folder.child_ids:
            name = os.path.basename(child.path)
            if name[:4] in [e + ' ' for e in IGNORED_ARTICLES if len(e) == 3]:
                index = name[4:][0]
            elif name[:3] in [e + ' ' for e in IGNORED_ARTICLES if len(e) == 2]:
                index = name[3:][0]
            else:
                index = name[0].upper()
            if index in num_list:
                index = '#'
            elif not index.isalnum():
                index = '?'

            indexes_dict.setdefault(index, [])
            indexes_dict[index].append(child)

        return indexes_dict

    def build_dict_indexes_artists(self, artists):
        indexes_dict = {}
        num_list = [str(x) for x in range(10)]
        for artist in artists:
            name = artist.name
            if name[:4] in [e + ' ' for e in IGNORED_ARTICLES if len(e) == 3]:
                index = name[4:][0]
            elif name[:3] in [e + ' ' for e in IGNORED_ARTICLES if len(e) == 2]:
                index = name[3:][0]
            else:
                index = name[0].upper()
            if index in num_list:
                index = '#'
            elif not index.isalnum():
                index = '?'

            indexes_dict.setdefault(index, [])
            indexes_dict[index].append(artist)

        return indexes_dict

    def make_MusicFolders(self):
        return etree.Element('musicFolders')

    def make_MusicFolder(self, folder):
        return etree.Element(
            'musicFolder',
            id=str(folder.id),
            name=folder.name or os.path.basename(folder.path),
        )

    def make_Indexes(self, folder):
        return etree.Element(
            'indexes',
            lastModified=str(folder.last_modification*1000),
            ignoredArticles=' '.join(IGNORED_ARTICLES),
        )

    def make_Index(self, index):
        return etree.Element('index', name=index)

    def make_Artist(self, folder, tag_name='artist'):
        elem_artist = etree.Element(
            tag_name,
            id=str(folder.id),
            name=os.path.basename(folder.path),
        )

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.10.2']:
            if folder.star == '1':
                elem_artist.set('starred', folder.write_date.replace(' ', 'T') + 'Z')

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.13.0']:
            if folder.rating and folder.rating != '0':
                elem_artist.set('userRating', folder.rating)
                elem_artist.set('averageRating', folder.rating)

        return elem_artist

    def make_Child_track(self, track, tag_name='child'):
        elem_track = etree.Element(
            tag_name,
            id=str(track.id),
            parent=str(track.folder_id.id),
            isDir='false',
            size=str(os.path.getsize(track.path)),
            contentType=mimetypes.guess_type(track.path)[0],
            suffix=os.path.splitext(track.path)[1].lstrip('.'),
            transcodedContentType='audio/mpeg',
            transcodedSuffix='mp3',
            duration=str(track.duration),
            bitRate=str(track.bitrate),
            path=os.path.basename(track.path),
        )

        if track.name:
            elem_track.set('title', track.name)
        if track.album_id:
            elem_track.set('album', track.album_id.name)
        if track.artist_id:
            elem_track.set('artist', track.artist_id.name)
        if track.track_number:
            try:
                track_number = track.track_number.split('/')[0]
                int(track_number)
                elem_track.set('track', track_number)
            except ValueError:
                _logger.warn(
                    'Could not convert track number %s of track id %s to integer',
                    track.track_number, track.id
                )
        if track.year:
            elem_track.set('year', track.year[:4])
        if track.genre_id:
            elem_track.set('genre', track.genre_id.name)

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.4.0']:
            elem_track.set('isVideo', 'false')
        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.6.0']:
            if track.rating and track.rating != '0':
                elem_track.set('userRating', track.rating)
                elem_track.set('averageRating', track.rating)
        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.14.0']:
            elem_track.set('playCount', str(track.play_count))
        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.8.0']:
            if track.disc:
                try:
                    disc = track.disc.split('/')[0]
                    int(disc)
                    elem_track.set('discNumber', disc)
                except ValueError:
                    _logger.warn(
                        'Could not convert disc number %s of track id %s to integer',
                        track.disc, track.id
                    )
            elem_track.set('created', track.create_date.replace(' ', 'T') + 'Z')
            if track.star == '1':
                elem_track.set('starred', track.write_date.replace(' ', 'T') + 'Z')
            elem_track.set('albumId', str(track.album_id.id))
            elem_track.set('artistId', str(track.artist_id.id))
            elem_track.set('type', 'music')
        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.10.2']:
            elem_track.set('bookmarkPosition', '0.0')

        return elem_track

    def make_Child_folder(self, folder, tag_name='child'):
        # Creates a new recordset to fetch only data of the required folder
        folder = folder[0] if folder else folder

        elem_directory = etree.Element(
            tag_name,
            id=str(folder.id),
            isDir='true',
            title=os.path.basename(folder.path),
            path=folder.path,
        )

        if folder.image_medium:
            elem_directory.set('coverArt', str(folder.id))

        if folder.track_ids:
            track = folder.track_ids[0]
            if track.album_id.name:
                elem_directory.set('album', track.album_id.name)
            if track.artist_id.name:
                elem_directory.set('artist', track.artist_id.name)
            if track.year:
                elem_directory.set('year', track.year[:4])
            if track.genre_id.name:
                elem_directory.set('genre', track.genre_id.name)
            if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.8.0']:
                if track.disc:
                    try:
                        disc = track.disc.split('/')[0]
                        int(disc)
                        elem_directory.set('discNumber', disc)
                    except ValueError:
                        _logger.warn(
                            'Could not convert disc number %s of track id %s to integer',
                            track.disc, track.id
                        )
                if track.album_id:
                    elem_directory.set('albumId', str(track.album_id.id))
                if track.artist_id:
                    elem_directory.set('artistId', str(track.artist_id.id))

        if folder.parent_id:
            elem_directory.set('parent', str(folder.parent_id.id))

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.6.0']:
            if folder.rating and folder.rating != '0':
                elem_directory.set('userRating', folder.rating)
                elem_directory.set('averageRating', folder.rating)

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.14.0']:
            elem_directory.set('playCount', str(sum(folder.track_ids.mapped('play_count'))))

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.8.0']:
            elem_directory.set('created', folder.create_date.replace(' ', 'T') + 'Z')

        return elem_directory

    def make_Directory(self, folder):
        elem_directory = etree.Element(
            'directory',
            id=str(folder.id),
            name=os.path.basename(folder.path),
        )
        if folder.parent_id:
            elem_directory.set('parent', str(folder.parent_id.id))

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.10.2']:
            if folder.star == '1':
                elem_directory.set('starred', folder.write_date.replace(' ', 'T') + 'Z')

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.13.0']:
            if folder.rating and folder.rating != '0':
                elem_directory.set('userRating', folder.rating)
                elem_directory.set('averageRating', folder.rating)

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.14.0']:
            elem_directory.set('playCount', str(sum(folder.track_ids.mapped('play_count'))))

        return elem_directory

    def make_Genres(self):
        elem_genres = etree.Element('genres')

        for k, v in self._get_genres_data().items():
            elem_genre = etree.Element('genre')
            elem_genre.text = k
            elem_genre.set('songCount', v.get('tracks', '0'))
            elem_genre.set('albumCount', v.get('albums', '0'))
            elem_genres.append(elem_genre)

        return elem_genres

    def _get_genres_data(self):
        folder_sharing = (
            'inactive' if request.env.ref('oomusic.oomusic_track').sudo().perm_read else 'active'
        )
        query = [
            'SELECT g.name, count(t.id)',
            'FROM oomusic_genre AS g',
            'JOIN oomusic_track AS t ON g.id = t.genre_id',
            'WHERE g.user_id = {}'.format(request.env.user.id),
            'GROUP BY g.name, g.id',
            'ORDER BY g.id',
        ]
        if folder_sharing == 'active':
            del query[3]
        request.env.cr.execute(' '.join(query))
        res_tracks = request.env.cr.fetchall()

        query = [
            'SELECT g.name, count(a.id)',
            'FROM oomusic_genre AS g',
            'JOIN oomusic_album AS a ON g.id = a.genre_id',
            'WHERE g.user_id = {}'.format(request.env.user.id),
            'GROUP BY g.name, g.id',
            'ORDER BY g.id',
        ]
        if folder_sharing == 'active':
            del query[3]
        request.env.cr.execute(' '.join(query))
        res_albums = request.env.cr.fetchall()

        data = OrderedDict()
        for r in res_tracks + res_albums:
            data.setdefault(r[0], {})
        for r in res_tracks:
            data[r[0]]['tracks'] = str(r[1])
        for r in res_albums:
            data[r[0]]['albums'] = str(r[1])

        return data

    # def make_Genre(self, genre):
    #     elem_genre = etree.Element('genre')
    #     elem_genre.text = genre.name
    #     elem_genre.set('songCount', str(len(genre.track_ids)))
    #     elem_genre.set('albumCount', str(len(genre.album_ids)))
    #
    #     return elem_genre

    def make_ArtistsID3(self):
        elem_artists = etree.Element('artists')

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.10.2']:
            elem_artists.set('ignoredArticles', ' '.join(IGNORED_ARTICLES))

        return elem_artists

    def make_IndexID3(self, index):
        return etree.Element('index', name=index)

    def make_ArtistID3(self, artist, tag_name='artist'):
        elem_artist = etree.Element(
            tag_name,
            id=str(artist.id),
            name=artist.name,
            albumCount=str(len(artist.album_ids)),
        )

        if artist.star == '1':
            elem_artist.set('starred', artist.write_date.replace(' ', 'T') + 'Z')

        return elem_artist

    def make_AlbumID3(self, album):
        elem_album = etree.Element(
            'album',
            id=str(album.id),
            name=album.name,
            songCount=str(len(album.track_ids)),
            duration=str(sum(album.track_ids.mapped('duration'))),
            created=album.create_date.replace(' ', 'T') + 'Z',
        )

        if album.artist_id:
            elem_album.set('artist', album.artist_id.name)
            elem_album.set('artistId', str(album.artist_id.id))
        if album.image_medium:
            elem_album.set('coverArt', str(album.folder_id.id))
        if album.star == '1':
            elem_album.set('starred', album.write_date.replace(' ', 'T') + 'Z')

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.10.2']:
            if album.year:
                elem_album.set('year', album.year[:4])
            if album.genre_id:
                elem_album.set('genre', album.genre_id.name)

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.14.0']:
            elem_album.set('playCount', str(sum(album.track_ids.mapped('play_count'))))

        return elem_album

    def make_Videos(self):
        return etree.Element('videos')

    def _make_ArtistInfoBase(self, artist):
        list_artist_info = []

        # Info already on artist object
        if artist.fm_getinfo_bio:
            bio = etree.Element('biography')
            bio.text = artist.fm_getinfo_bio
            list_artist_info.append(bio)

        # Extra info
        req_json = artist._lastfm_artist_getinfo()

        if 'artist' in req_json and 'mbid' in req_json['artist']:
            mbid = etree.Element('musicBrainzId')
            mbid.text = req_json['artist']['mbid']
            list_artist_info.append(mbid)

        if 'artist' in req_json and 'url' in req_json['artist']:
            url = etree.Element('lastFmUrl')
            url.text = req_json['artist']['url']
            list_artist_info.append(url)

        if 'artist' in req_json and 'image' in req_json['artist']:
            for image in req_json['artist']['image']:
                if image.get('size') == 'large' and image['#text']:
                    img = etree.Element('smallImageUrl')
                    img.text = image['#text']
                    list_artist_info.append(img)
                elif image.get('size') == 'extralarge' and image['#text']:
                    img = etree.Element('mediumImageUrl')
                    img.text = image['#text']
                    list_artist_info.append(img)
                elif image.get('size') == 'mega' and image['#text']:
                    img = etree.Element('largeImageUrl')
                    img.text = image['#text']
                    list_artist_info.append(img)

        return list_artist_info

    def make_ArtistInfo(self, folder, count=20, includeNotPresent=False):
        elem_artist_info = etree.Element('artistInfo')

        # Stupid hack needed for AVSub which makes useless requests for folder with id '1'
        try:
            artist = request.env['oomusic.artist'].search([
                ('name', 'ilike', os.path.basename(folder.path))
            ])
        except AccessError:
            artist = False

        if artist:
            base_artist_info = self._make_ArtistInfoBase(artist[0])
            for elem in base_artist_info:
                elem_artist_info.append(elem)

        # TODO: support similar artists

        return elem_artist_info

    def make_ArtistInfo2(self, artist, count=20, includeNotPresent=False):
        elem_artist_info = etree.Element('artistInfo2')

        base_artist_info = self._make_ArtistInfoBase(artist)
        for elem in base_artist_info:
            elem_artist_info.append(elem)

        for s_artist in artist.fm_getsimilar_artist_ids[:count]:
            elem_similar_artist = self.make_ArtistID3(s_artist, tag_name='similarArtist')
            elem_artist_info.append(elem_similar_artist)

        return elem_artist_info

    def make_AlbumInfo(self, folder):
        album = request.env['oomusic.album'].search([
            ('name', 'ilike', os.path.basename(folder.path))
        ])
        if album:
            return self.make_AlbumInfo2(album[0])
        else:
            return etree.Element('albumInfo')

    def make_AlbumInfo2(self, album):
        elem_album_info = etree.Element('albumInfo')
        req_json = album._lastfm_album_getinfo()

        if 'album' in req_json and 'wiki' in req_json['album'] and 'summary' in req_json['album']['wiki']:
            notes = etree.Element('notes')
            notes.text = req_json['album']['wiki']['summary']
            elem_album_info.append(notes)
        else:
            notes = etree.Element('notes')
            elem_album_info.append(notes)

        if 'album' in req_json and 'mbid' in req_json['album']:
            mbid = etree.Element('musicBrainzId')
            mbid.text = req_json['album']['mbid']
            elem_album_info.append(mbid)

        if 'album' in req_json and 'url' in req_json['album']:
            url = etree.Element('lastFmUrl')
            url.text = req_json['album']['url']
            elem_album_info.append(url)

        if 'album' in req_json and 'image' in req_json['album']:
            for image in req_json['album']['image']:
                if image.get('size') == 'large' and image['#text']:
                    img = etree.Element('smallImageUrl')
                    img.text = image['#text']
                    elem_album_info.append(img)
                elif image.get('size') == 'extralarge' and image['#text']:
                    img = etree.Element('mediumImageUrl')
                    img.text = image['#text']
                    elem_album_info.append(img)
                elif image.get('size') == 'mega' and image['#text']:
                    img = etree.Element('largeImageUrl')
                    img.text = image['#text']
                    elem_album_info.append(img)

        return elem_album_info

    def make_SimilarSongs2(self, track, count=50, tag_name='similarSongs2'):
        elem_song_similar = etree.Element(tag_name)
        req_json = track._lastfm_track_getsimilar(count=count)

        try:
            s_tracks = request.env['oomusic.track']
            for s_track in req_json['similartracks']['track']:
                s_tracks |= request.env['oomusic.track'].search([
                    ('name', '=ilike', s_track['name']),
                    ('artist_id.name', '=ilike', s_track['artist']['name'])
                ], limit=1)
            for s_track in s_tracks:
                elem_song = self.make_Child_track(s_track, tag_name='song')
                elem_song_similar.append(elem_song)
        except:
            _logger.warning(
                'An error occurred while searching similar songs. json contains:\n%s',
                pformat(req_json), exc_info=True
            )

        return elem_song_similar

    def make_TopSongs(self, artist_name, count=50):
        elem_song_info = etree.Element('topSongs')

        artist = request.env['oomusic.artist'].search([('name', 'ilike', artist_name)])
        if artist:
            for track in artist[0].fm_gettoptracks_track_ids[:count]:
                elem_song_info.append(self.make_Child_track(track, tag_name='song'))

        return elem_song_info

    def make_AlbumList(self):
        return etree.Element('albumList')

    def make_AlbumList2(self):
        return etree.Element('albumList2')

    def make_listSongs(self, tag_name):
        return etree.Element(tag_name)

    def make_SearchResult(self, offset, totalHits):
        return etree.Element('searchResult', offset=offset, totalHits=totalHits)

    def make_SearchResult2(self, tag_name='searchResult2'):
        return etree.Element(tag_name)

    def make_Lyrics(self, artist=False, title=False):
        elem_lyrics = etree.Element('lyrics')
        if artist:
            elem_lyrics.set('artist', artist)
        if title:
            elem_lyrics.set('title', title)

        # TODO fetch lyrics

        return elem_lyrics

    def make_User(self, user):
        elem_user = etree.Element(
            'user',
            username=user.login,
            adminRole='false',
            settingsRole='false',
            downloadRole='true',
            uploadRole='false',
            playlistRole='true',
            coverArtRole='true',
            commentRole='true',
            podcastRole='false',
            streamRole='true',
            jukeboxRole='false',
        )

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.6.0']:
            elem_user.set('email', 'foo@bar.com')

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.7.0']:
            elem_user.set('scrobblingEnabled', 'false')
            elem_user.set('shareRole', 'false')

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.13.0']:
            elem_user.set('maxBitRate', '0')

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.14.0']:
            elem_user.set('videoConversionRole', 'false')
            elem_user.set('avatarLastChanged', user.write_date.replace(' ', 'T') + 'Z')

        folders = request.env['oomusic.folder'].search([
            ('user_id', '=', user.id), ('root', '=', True)
        ])
        for folder in folders:
            xml_folder = etree.Element('folder')
            xml_folder.text = str(folder.id)
            elem_user.append(xml_folder)

        return elem_user

    def make_Users(self):
        return etree.Element('users')

    def make_Playlists(self):
        return etree.Element('playlists')

    def make_Playlist(self, playlist):
        elem_playlist = etree.Element(
            'playlist',
            id=str(playlist.id),
            name=playlist.name,
            )

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.8.0']:
            if playlist.comment:
                elem_playlist.set('comment', playlist.comment)
            elem_playlist.set('owner', playlist.user_id.login)
            elem_playlist.set('public', 'false')
            elem_playlist.set('songCount', str(len(playlist.playlist_line_ids)))
            elem_playlist.set(
                'duration',
                str(sum(playlist.playlist_line_ids.mapped('track_id').mapped('duration')))
            )
            elem_playlist.set('created', playlist.create_date.replace(' ', 'T') + 'Z')

            elem_allowed_user = etree.Element('allowedUser')
            elem_allowed_user.text = playlist.user_id.login
            elem_playlist.append(elem_allowed_user)

        if API_VERSION_LIST[self.version_client] >= API_VERSION_LIST['1.13.0']:
            elem_playlist.set('changed', playlist.write_date.replace(' ', 'T') + 'Z')

        return elem_playlist

    def make_Shares(self):
        return etree.Element('shares')

    def make_Podcasts(self, tag_name='podcasts'):
        return etree.Element(tag_name)

    def make_InternetRadioStations(self):
        return etree.Element('internetRadioStations')

    def make_ChatMessages(self):
        return etree.Element('chatMessages')

    def make_Bookmarks(self):
        return etree.Element('bookmarks')

    def make_ScanStatus(self, folders, scan=None):
        return etree.Element(
            'scanStatus',
            scanning=str(any(f.locked for f in folders) if scan is not None else scan).lower(),
            count=str(request.env['oomusic.track'].search_count([])),
            )
