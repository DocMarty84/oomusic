# -*- coding: utf-8 -*-

import hashlib
import os
import shutil
from multiprocessing import cpu_count
from tempfile import gettempdir

from odoo import fields

from . import test_common


class TestOomusicConverter(test_common.TestOomusicCommon):
    def test_00_create_interact(self):
        """
        Test creation and basic interaction
        """
        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)
        conv = self.ConverterObj.create({})

        # Check default data
        data_default = (
            conv.name,
            conv.user_id,
            conv.state,
            conv.transcoder_id,
            conv.dest_folder,
            conv.max_threads,
            conv.norm,
            conv.progress,
            conv.show_waiting,
        )
        data_ref = (
            fields.Date.to_string(fields.Date.context_today(conv)),
            self.env.user,
            u"draft",
            self.env.ref("oomusic.oomusic_transcoder_0"),
            os.path.join(
                gettempdir(), "koozic", fields.Date.to_string(fields.Date.context_today(conv))
            ),
            cpu_count(),
            False,
            0.0,
            False,
        )
        self.assertEqual(data_default, data_ref)

        # _onchange_album_id
        album1 = self.AlbumObj.search([("name", "=", "Album1")])
        conv.album_id = album1
        conv._onchange_album_id()
        self.assertEqual(conv.album_id, self.AlbumObj)
        self.assertEqual(
            conv.mapped("converter_line_ids").mapped("track_id").mapped("name"),
            [u"Song1", u"Song2"],
        )
        conv.action_purge()

        # _onchange_artist_id
        artist1 = self.ArtistObj.search([("name", "=", "Artist1")])
        conv.artist_id = artist1
        conv._onchange_artist_id()
        self.assertEqual(conv.artist_id, self.ArtistObj)
        self.assertEqual(
            conv.mapped("converter_line_ids").mapped("track_id").mapped("name"),
            [u"Song3", u"Song4", u"Song1", u"Song2"],
        )
        conv.action_purge()

        # _onchange_playlist_id
        artist2 = self.ArtistObj.search([("name", "=", "Artist2")])
        artist2.action_add_to_playlist()
        playlist = self.PlaylistObj.search([("current", "=", True)], limit=1)
        conv.playlist_id = playlist
        conv._onchange_playlist_id()
        self.assertEqual(conv.playlist_id, self.PlaylistObj)
        self.assertEqual(
            conv.mapped("converter_line_ids").mapped("track_id").mapped("name"),
            [u"Song5", u"Song6"],
        )
        conv.action_purge()

        # _onchange_transcoder_id
        conv._onchange_transcoder_id()
        self.assertEqual(conv.bitrate, self.env.ref("oomusic.oomusic_transcoder_0").bitrate)

        # action_run
        conv.artist_id = artist2
        conv._onchange_artist_id()
        conv.action_run()
        conv.invalidate_cache()
        self.assertEqual(conv.state, u"running")
        self.assertEqual(conv.converter_line_ids.mapped("state"), [u"waiting", u"waiting"])

        # action_cancel
        conv.action_cancel()
        conv.invalidate_cache()
        self.assertEqual(conv.state, u"cancel")
        self.assertEqual(conv.converter_line_ids.mapped("state"), [u"cancel", u"cancel"])

        # action_draft
        conv.action_draft()
        conv.invalidate_cache()
        self.assertEqual(conv.state, u"draft")
        self.assertEqual(conv.converter_line_ids.mapped("state"), [u"draft", u"draft"])

        self.cleanUp()

    def test_10_convert(self):
        """
        Test conversion when files are converted thanks to FFMpeg
        """

        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)
        conv = self.ConverterObj.create({})

        conv.album_id = self.AlbumObj.search([("name", "=", "Album1")])
        conv.bitrate = 92
        conv._onchange_album_id()
        conv.action_run()
        conv.invalidate_cache()
        conv.with_context(test_mode=True).action_convert()

        self.assertEqual(conv.state, u"done")
        # self.assertEqual(conv.converter_line_ids.mapped("state"), [u"done", u"done"])
        path = os.path.join(conv.dest_folder, u"Artist1", u"Album1")
        file1 = os.path.join(path, u"song1.mp3")
        file2 = os.path.join(path, u"song2.mp3")
        self.assertEqual(path, path)
        self.assertEqual(file1, file1)
        self.assertEqual(file2, file2)

        sha1 = {}
        for path in conv.converter_line_ids.mapped("track_id").mapped("path") + [file1, file2]:
            sha1[path] = hashlib.sha1()
            with open(path, "rb") as f:
                while True:
                    data = f.read(65536)
                    if not data:
                        sha1[path] = sha1[path].hexdigest()
                        break
                    sha1[path].update(data)
        self.assertEqual(len(set(sha1.values())), 4)

        self.cleanUp()
        shutil.rmtree(conv.dest_folder, True)

    def test_20_convert_copy(self):
        """
        Test conversion when files are copied to avoid upsampling
        """

        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)
        conv = self.ConverterObj.create({})

        conv.album_id = self.AlbumObj.search([("name", "=", "Album1")])
        conv.bitrate = 320
        conv._onchange_album_id()
        conv.action_run()
        conv.invalidate_cache()
        conv.with_context(test_mode=True).action_convert()

        self.assertEqual(conv.state, u"done")
        # self.assertEqual(conv.converter_line_ids.mapped("state"), [u"done", u"done"])
        path = os.path.join(conv.dest_folder, u"Artist1", u"Album1")
        file1 = os.path.join(path, u"song1.mp3")
        file2 = os.path.join(path, u"song2.mp3")
        self.assertEqual(path, path)
        self.assertEqual(file1, file1)
        self.assertEqual(file2, file2)

        sha1 = {}
        for path in conv.converter_line_ids.mapped("track_id").mapped("path") + [file1, file2]:
            sha1[path] = hashlib.sha1()
            with open(path, "rb") as f:
                while True:
                    data = f.read(65536)
                    if not data:
                        sha1[path] = sha1[path].hexdigest()
                        break
                    sha1[path].update(data)
        self.assertEqual(len(set(sha1.values())), 2)

        self.cleanUp()
        shutil.rmtree(conv.dest_folder, True)
