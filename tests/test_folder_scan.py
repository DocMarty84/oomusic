# -*- coding: utf-8 -*-

import os
import shutil
import time

import taglib
from . import test_common


class TestOomusicFolderScan(test_common.TestOomusicCommon):

    def test_00_initial_scan(self):
        '''
        Test a simple scan of the folder
        '''
        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)
        Tracks = self.TrackObj.search([('root_folder_id', '=', self.Folder.id)])
        Albums = self.AlbumObj.search([('name', 'in', ['Album1', 'Album2', 'Album3'])])

        # Verify the music.track data
        self.assertEqual(
            set(Tracks.mapped('name')),
            set(['Song1', 'Song2', 'Song3', 'Song4', 'Song5', 'Song6'])
        )
        ref_data = {
            'Song1': (u'Artist1', u'Album1', u'Genre1', u'2001'),
            'Song2': (u'Artist1', u'Album1', u'Genre1', u'2001'),
            'Song3': (u'Artist1', u'Album2', u'Genre2', u'2002'),
            'Song4': (u'Artist1', u'Album2', u'Genre2', u'2002'),
            'Song5': (u'Artist2', u'Album3', u'Genre3', u'2003'),
            'Song6': (u'Artist2', u'Album3', u'Genre3', u'2003'),
        }
        for Track in Tracks:
            self.assertEqual(
                ref_data[Track.name],
                (Track.artist_id.name, Track.album_id.name, Track.genre_id.name, Track.year)
            )

        # Verify the music.album data.
        self.assertEqual(
            set(Albums.mapped('name')),
            set(['Album1', 'Album2', 'Album3'])
        )
        ref_data = {
            'Album1': (2, u'Artist1', u'Genre1', u'2001'),
            'Album2': (2, u'Artist1', u'Genre2', u'2002'),
            'Album3': (2, u'Artist2', u'Genre3', u'2003'),
        }
        for Album in Albums:
            self.assertEqual(
                ref_data[Album.name],
                (len(Album.track_ids), Album.artist_id.name, Album.genre_id.name, Album.year)
            )

        self.cleanUp()

    def test_10_modify_tags(self):
        '''
        Test a modification of the tags of existing tracks.
        '''
        # Initial scan
        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)

        time.sleep(2)  # make sure we can detect a modification time in the files
        # Modify the tags
        new_tags = {
            'Song1': {'DATE': '2011'},
            'Song2': {'DATE': '2011'},
            'Song3': {'GENRE': 'GENRE4'},
            'Song4': {'GENRE': 'GENRE4'},
            'Song5': {
                'ARTIST': 'ARTIST3',
                'ALBUMARTIST': 'ARTIST3',
            },
            'Song6': {
                'ARTIST': 'ARTIST3',
                'ALBUMARTIST': 'ARTIST3',
            },
        }
        Tracks = self.TrackObj.search([('root_folder_id', '=', self.Folder.id)])
        for Track in Tracks:
            song = taglib.File(Track.path)
            new_tag = new_tags[Track.name]
            for k, v in new_tag.items():
                song.tags[k] = [v]
            song.save()
            os.utime(Track.path, None)

        Folders = self.FolderObj.search([('id', 'child_of', self.Folder.id)])
        for Folder in Folders:
            os.utime(Folder.path, None)

        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)
        Tracks = self.TrackObj.search([('root_folder_id', '=', self.Folder.id)])
        Albums = self.AlbumObj.search([('name', 'in', ['Album1', 'Album2', 'Album3'])])

        # Verify the music.track data
        self.assertEqual(
            set(Tracks.mapped('name')),
            set(['Song1', 'Song2', 'Song3', 'Song4', 'Song5', 'Song6'])
        )
        ref_data = {
            'Song1': (u'Artist1', u'Album1', u'Genre1', u'2011'),
            'Song2': (u'Artist1', u'Album1', u'Genre1', u'2011'),
            'Song3': (u'Artist1', u'Album2', u'GENRE4', u'2002'),
            'Song4': (u'Artist1', u'Album2', u'GENRE4', u'2002'),
            'Song5': (u'ARTIST3', u'Album3', u'Genre3', u'2003'),
            'Song6': (u'ARTIST3', u'Album3', u'Genre3', u'2003'),
        }
        for Track in Tracks:
            self.assertEqual(
                ref_data[Track.name],
                (Track.artist_id.name, Track.album_id.name, Track.genre_id.name, Track.year)
            )

        # Verify the music.album data.
        self.assertEqual(
            set(Albums.mapped('name')),
            set(['Album1', 'Album2', 'Album3'])
        )
        ref_data = {
            'Album1': (2, u'Artist1', u'Genre1', u'2011'),
            'Album2': (2, u'Artist1', u'GENRE4', u'2002'),
            'Album3': (2, u'ARTIST3', u'Genre3', u'2003'),
        }
        for Album in Albums:
            self.assertEqual(
                ref_data[Album.name],
                (len(Album.track_ids), Album.artist_id.name, Album.genre_id.name, Album.year)
            )

        # Check useless data have been removed
        Genre = self.GenreObj.search([('name', '=', 'Genre2')])
        self.assertEqual(0, len(Genre))
        Artist = self.ArtistObj.search([('name', '=', 'Artist2')])
        self.assertEqual(0, len(Artist))

        self.cleanUp()

    def test_20_rename_dir(self):
        '''
        Test a renaming of directory.
        '''
        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)

        shutil.move(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'folder_scan_test', 'Artist1'),
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'folder_scan_test', 'Artist3')
        )

        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)
        Tracks = self.TrackObj.search([('root_folder_id', '=', self.Folder.id)])
        Albums = self.AlbumObj.search([('name', 'in', ['Album1', 'Album2', 'Album3'])])

        # Verify the music.track data
        self.assertEqual(
            set(Tracks.mapped('name')),
            set(['Song1', 'Song2', 'Song3', 'Song4', 'Song5', 'Song6'])
        )
        ref_data = {
            'Song1': (u'Artist1', u'Album1', u'Genre1', u'2001'),
            'Song2': (u'Artist1', u'Album1', u'Genre1', u'2001'),
            'Song3': (u'Artist1', u'Album2', u'Genre2', u'2002'),
            'Song4': (u'Artist1', u'Album2', u'Genre2', u'2002'),
            'Song5': (u'Artist2', u'Album3', u'Genre3', u'2003'),
            'Song6': (u'Artist2', u'Album3', u'Genre3', u'2003'),
        }
        for Track in Tracks:
            self.assertEqual(
                ref_data[Track.name],
                (Track.artist_id.name, Track.album_id.name, Track.genre_id.name, Track.year)
            )

        # Verify the music.album data.
        self.assertEqual(
            set(Albums.mapped('name')),
            set(['Album1', 'Album2', 'Album3'])
        )
        ref_data = {
            'Album1': (2, u'Artist1', u'Genre1', u'2001'),
            'Album2': (2, u'Artist1', u'Genre2', u'2002'),
            'Album3': (2, u'Artist2', u'Genre3', u'2003'),
        }
        for Album in Albums:
            self.assertEqual(
                ref_data[Album.name],
                (len(Album.track_ids), Album.artist_id.name, Album.genre_id.name, Album.year)
            )

        # Verify the music.folder data
        Folder = self.FolderObj.search([('name', 'like', 'Artist1')])
        self.assertEqual(0, len(Folder))

        self.cleanUp()

    def test_30_remove_dir(self):
        '''
        Test a removing of directory.
        '''
        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)

        shutil.rmtree(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'folder_scan_test', 'Artist1'),
            True
        )

        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)
        Tracks = self.TrackObj.search([('root_folder_id', '=', self.Folder.id)])
        Albums = self.AlbumObj.search([('name', 'in', ['Album1', 'Album2', 'Album3'])])

        # Verify the music.track data
        self.assertEqual(
            set(Tracks.mapped('name')),
            set(['Song5', 'Song6'])
        )
        ref_data = {
            'Song5': (u'Artist2', u'Album3', u'Genre3', u'2003'),
            'Song6': (u'Artist2', u'Album3', u'Genre3', u'2003'),
        }
        for Track in Tracks:
            self.assertEqual(
                ref_data[Track.name],
                (Track.artist_id.name, Track.album_id.name, Track.genre_id.name, Track.year)
            )

        # Verify the music.album data.
        self.assertEqual(
            set(Albums.mapped('name')),
            set(['Album3'])
        )
        ref_data = {
            'Album3': (2, u'Artist2', u'Genre3', u'2003'),
        }
        for Album in Albums:
            self.assertEqual(
                ref_data[Album.name],
                (len(Album.track_ids), Album.artist_id.name, Album.genre_id.name, Album.year)
            )

        # Verify the music.folder data
        Folder = self.FolderObj.search([('name', 'like', 'Artist1')])
        self.assertEqual(0, len(Folder))

        self.cleanUp()
