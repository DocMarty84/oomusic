# -*- coding: utf-8 -*-

import os

from . import test_sub_common


class TestOomusicSubBrowsing(test_sub_common.TestOomusicSubCommon):

    def test_00_getMusicFolders(self):
        '''
        Test getMusicFolders method
        '''
        self.env2.cr.release()
        res = self.url_open('/rest/getMusicFolders.view' + self.cred).read()
        res_clean = ''.join(res.split('\n')[2:][:-2])
        self.assertEqual(
            res_clean,
            '  <musicFolders>'
            '    <musicFolder id="{}" name="folder_scan_test"/>'
            '  </musicFolders>'.format(self.Folder.id)
        )
        self.cleanUp()

    def test_05_getIndexes(self):
        '''
        Test getIndexes method
        '''
        tracks = self.TrackObj.search([])
        folders = self.FolderObj.search([])
        self.env2.cr.release()

        # No params
        res = self.url_open('/rest/getIndexes.view' + self.cred).read()
        res_clean = ''.join(res.split('\n')[2:][:-2])
        data = {
            'f1_last': folders[0].last_modification*1000,
            'f2_id': folders[1].id,
            'f2_name': os.path.basename(folders[1].path),
            'f3_id': folders[4].id,
            'f3_name': os.path.basename(folders[4].path),
        }
        self.assertEqual(
            res_clean,
            '  <indexes ignoredArticles="The El La Los Las Le Les" lastModified="{f1_last}">'
            '    <index name="A">'
            '      <artist id="{f2_id}" name="{f2_name}"/>'
            '      <artist id="{f3_id}" name="{f3_name}"/>'
            '    </index>'
            '  </indexes>'.format(**data)
        )

        # params: musicFolderId (artist)
        url = '/rest/getIndexes.view' + self.cred + '&musicFolderId={}'.format(folders[1].id)
        res = self.url_open(url).read()
        res_clean = ''.join(res.split('\n')[2:][:-2])
        data = {
            'f1_last': folders[1].last_modification*1000,
            'f2_id': folders[2].id,
            'f2_name': os.path.basename(folders[2].path),
            'f3_id': folders[3].id,
            'f3_name': os.path.basename(folders[3].path),
        }
        self.assertEqual(
            res_clean,
            '  <indexes ignoredArticles="The El La Los Las Le Les" lastModified="{f1_last}">'
            '    <index name="A">'
            '      <artist id="{f2_id}" name="{f2_name}"/>'
            '      <artist id="{f3_id}" name="{f3_name}"/>'
            '    </index>'
            '  </indexes>'.format(**data)
        )

        # params: musicFolderId (album)
        url = '/rest/getIndexes.view' + self.cred + '&musicFolderId={}'.format(folders[2].id)
        res = self.url_open(url).read()
        res_clean = ''.join(res.split('\n')[2:][:-2])
        data = {
            'f1_last': folders[2].last_modification*1000,
            't1_id': tracks[4].id,
            't1_parent': tracks[4].folder_id.id,
            't1_path': os.path.basename(tracks[4].path),
            't1_album': tracks[4].album_id.name,
            't1_artist': tracks[4].artist_id.name,
            't1_num': tracks[4].track_number,
            't1_year': tracks[4].year,
            't1_genre': tracks[4].genre_id.name,
            't1_create': tracks[4].create_date.replace(' ', 'T') + 'Z',
            't1_album_id': tracks[4].album_id.id,
            't1_artist_id': tracks[4].artist_id.id,
            't2_id': tracks[5].id,
            't2_parent': tracks[5].folder_id.id,
            't2_path': os.path.basename(tracks[5].path),
            't2_album': tracks[5].album_id.name,
            't2_artist': tracks[5].artist_id.name,
            't2_num': tracks[5].track_number,
            't2_year': tracks[5].year,
            't2_genre': tracks[5].genre_id.name,
            't2_create': tracks[5].create_date.replace(' ', 'T') + 'Z',
            't2_album_id': tracks[5].album_id.id,
            't2_artist_id': tracks[5].artist_id.id,
        }
        self.assertEqual(
            res_clean,
            '  <indexes ignoredArticles="The El La Los Las Le Les" lastModified="{f1_last}">'
            '    <child bitRate="131" contentType="audio/mpeg" duration="1" id="{t1_id}" isDir="false" parent="{t1_parent}" path="{t1_path}" size="18287" suffix="mp3" transcodedContentType="audio/mpeg" transcodedSuffix="mp3" title="Song1" album="{t1_album}" artist="{t1_artist}" track="{t1_num}" year="{t1_year}" genre="{t1_genre}" isVideo="false" playCount="0" created="{t1_create}" albumId="{t1_album_id}" artistId="{t1_artist_id}" type="music" bookmarkPosition="0.0"/>'
            '    <child bitRate="131" contentType="audio/mpeg" duration="1" id="{t2_id}" isDir="false" parent="{t2_parent}" path="{t2_path}" size="18287" suffix="mp3" transcodedContentType="audio/mpeg" transcodedSuffix="mp3" title="Song2" album="{t2_album}" artist="{t2_artist}" track="{t2_num}" year="{t2_year}" genre="{t2_genre}" isVideo="false" playCount="0" created="{t2_create}" albumId="{t2_album_id}" artistId="{t2_artist_id}" type="music" bookmarkPosition="0.0"/>'
            '  </indexes>'.format(**data)
        )
        self.cleanUp()

    def test_10_getMusicDirectory(self):
        '''
        Test getMusicDirectory method
        '''
        albums = self.AlbumObj.search([])
        tracks = self.TrackObj.search([])
        folders = self.FolderObj.search([])
        self.env2.cr.release()

        # params: musicFolderId (artist)
        url = '/rest/getMusicDirectory.view' + self.cred + '&id={}'.format(folders[1].id)
        res = self.url_open(url).read()
        res_clean = ''.join(res.split('\n')[2:][:-2])
        data = {
            'f1_id': folders[1].id,
            'f1_name': os.path.basename(folders[1].path),
            'f1_parent': folders[0].id,
            'f2_id': folders[2].id,
            'f2_path': folders[2].path,
            'f2_name': os.path.basename(folders[2].path),
            'f2_album': albums[2].name,
            'f2_artist': albums[2].artist_id.name,
            'f2_year': albums[2].year,
            'f2_genre': albums[2].genre_id.name,
            'f2_album_id': albums[2].id,
            'f2_artist_id': albums[2].artist_id.id,
            'f2_parent': folders[1].id,
            'f2_create': folders[2].create_date.replace(' ', 'T') + 'Z',
            'f3_id': folders[3].id,
            'f3_path': folders[3].path,
            'f3_name': os.path.basename(folders[3].path),
            'f3_album': albums[1].name,
            'f3_artist': albums[1].artist_id.name,
            'f3_year': albums[1].year,
            'f3_genre': albums[1].genre_id.name,
            'f3_album_id': albums[1].id,
            'f3_artist_id': albums[1].artist_id.id,
            'f3_parent': folders[1].id,
            'f3_create': folders[3].create_date.replace(' ', 'T') + 'Z',
        }
        self.assertEqual(
            res_clean,
            '  <directory id="{f1_id}" name="{f1_name}" parent="{f1_parent}" playCount="0">'
            '    <child id="{f2_id}" isDir="true" path="{f2_path}" title="{f2_name}" album="{f2_album}" artist="{f2_artist}" year="{f2_year}" genre="{f2_genre}" albumId="{f2_album_id}" artistId="{f2_artist_id}" parent="{f2_parent}" playCount="0" created="{f2_create}"/>'
            '    <child id="{f3_id}" isDir="true" path="{f3_path}" title="{f3_name}" album="{f3_album}" artist="{f3_artist}" year="{f3_year}" genre="{f3_genre}" albumId="{f3_album_id}" artistId="{f3_artist_id}" parent="{f3_parent}" playCount="0" created="{f3_create}"/>'
            '  </directory>'.format(**data)
        )

        # params: musicFolderId (album)
        url = '/rest/getMusicDirectory.view' + self.cred + '&id={}'.format(folders[2].id)
        res = self.url_open(url).read()
        res_clean = ''.join(res.split('\n')[2:][:-2])
        data = {
            'f1_id': folders[2].id,
            'f1_name': os.path.basename(folders[2].path),
            'f1_parent': folders[1].id,
            't1_id': tracks[4].id,
            't1_parent': tracks[4].folder_id.id,
            't1_path': os.path.basename(tracks[4].path),
            't1_name': tracks[4].name,
            't1_album': tracks[4].album_id.name,
            't1_artist': tracks[4].artist_id.name,
            't1_num': tracks[4].track_number,
            't1_year': tracks[4].year,
            't1_genre': tracks[4].genre_id.name,
            't1_create': tracks[4].create_date.replace(' ', 'T') + 'Z',
            't1_album_id': tracks[4].album_id.id,
            't1_artist_id': tracks[4].artist_id.id,
            't2_id': tracks[5].id,
            't2_parent': tracks[5].folder_id.id,
            't2_path': os.path.basename(tracks[5].path),
            't2_name': tracks[5].name,
            't2_album': tracks[5].album_id.name,
            't2_artist': tracks[5].artist_id.name,
            't2_num': tracks[5].track_number,
            't2_year': tracks[5].year,
            't2_genre': tracks[5].genre_id.name,
            't2_create': tracks[5].create_date.replace(' ', 'T') + 'Z',
            't2_album_id': tracks[5].album_id.id,
            't2_artist_id': tracks[5].artist_id.id,
        }
        self.assertEqual(
            res_clean,
            '  <directory id="{f1_id}" name="{f1_name}" parent="{f1_parent}" playCount="0">'
            '    <child bitRate="131" contentType="audio/mpeg" duration="1" id="{t1_id}" isDir="false" parent="{t1_parent}" path="{t1_path}" size="18287" suffix="mp3" transcodedContentType="audio/mpeg" transcodedSuffix="mp3" title="{t1_name}" album="{t1_album}" artist="{t1_artist}" track="{t1_num}" year="{t1_year}" genre="{t1_genre}" isVideo="false" playCount="0" created="{t1_create}" albumId="{t1_album_id}" artistId="{t1_artist_id}" type="music" bookmarkPosition="0.0"/>'
            '    <child bitRate="131" contentType="audio/mpeg" duration="1" id="{t2_id}" isDir="false" parent="{t2_parent}" path="{t2_path}" size="18287" suffix="mp3" transcodedContentType="audio/mpeg" transcodedSuffix="mp3" title="{t2_name}" album="{t2_album}" artist="{t2_artist}" track="{t2_num}" year="{t2_year}" genre="{t2_genre}" isVideo="false" playCount="0" created="{t2_create}" albumId="{t2_album_id}" artistId="{t2_artist_id}" type="music" bookmarkPosition="0.0"/>'
            '  </directory>'.format(**data)
        )
        self.cleanUp()

    def test_15_getGenres(self):
        '''
        Test getGenres method
        '''
        genres = self.GenreObj.search([])
        self.env2.cr.release()

        # params: musicFolderId (artist)
        url = '/rest/getGenres.view' + self.cred
        res = self.url_open(url).read()
        res_clean = ''.join(res.split('\n')[2:][:-2])
        data = {
            'g1_name': genres[0].name,
            'g2_name': genres[1].name,
            'g3_name': genres[2].name,
        }
        self.assertEqual(
            res_clean,
            '  <genres>'
            '    <genre songCount="2" albumCount="1">{g1_name}</genre>'
            '    <genre songCount="2" albumCount="1">{g3_name}</genre>'
            '    <genre songCount="2" albumCount="1">{g2_name}</genre>'
            '  </genres>'.format(**data)
        )
        self.cleanUp()
