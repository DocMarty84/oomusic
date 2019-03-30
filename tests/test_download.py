# -*- coding: utf-8 -*-

import hashlib

from . import test_common
from . import test_sub_common


class TestOomusicDownload(test_common.TestOomusicCommon):
    def test_00_url_creation(self):
        """
        Test creation of links
        """
        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)
        track = self.TrackObj.search([], limit=1)
        album = self.AlbumObj.search([], limit=1)
        artist = self.ArtistObj.search([], limit=1)
        genre = self.GenreObj.search([], limit=1)

        track.action_create_download_link()
        album.action_create_download_link()
        artist.action_create_download_link()
        genre.action_create_download_link()

        for down in track, album, artist, genre:
            link = self.env["oomusic.download"].search(
                [("res_model", "=", down._name), ("res_id", "=", down.id)]
            )
            self.assertEqual(len(link), 1)
        self.cleanUp()


class TestOomusicDownloadController(test_sub_common.TestOomusicSubCommon):
    def test_00_url_access(self):
        """
        Test url access
        """
        # Access with incorrect token
        res = self.url_open("/oomusic/down?token=abc")
        self.assertEqual(res.status_code, 404)

        # Access with correct token
        track = self.TrackObj.search([("name", "=", "Song1")])
        track.action_create_download_link()
        link = self.env["oomusic.download"].search(
            [("res_model", "=", track._name), ("res_id", "=", track.id)]
        )
        self.assertEqual(len(link), 1)
        res = self.url_open(link.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            hashlib.sha1(res.content).hexdigest(), "ac6d0d6e361ba97bfe20f60da550ea15484f4e4c"
        )

        # Too many accesses
        res = self.url_open(link.url)
        self.assertEqual(res.status_code, 403)
        self.cleanUp()
