# -*- coding: utf-8 -*-

import json
import os

from . import test_common


class TestOomusicFolder(test_common.TestOomusicCommon):
    def test_00_write_path(self):
        """
        Test writing path
        """
        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)
        norm_path = self.Folder.path

        self.Folder.write({"path": self.Folder.path + os.path.sep})

        folders = self.Folder | self.Folder.search([("id", "child_of", self.Folder.ids)])
        tracks = folders.mapped("track_ids")
        self.assertEqual(self.Folder.path, norm_path)
        self.assertEqual(len(folders), 6)
        self.assertEqual(len(tracks), 6)

        self.assertEqual(set(folders.mapped("last_modification")), set([0]))
        self.assertEqual(set(tracks.mapped("last_modification")), set([0]))

        self.cleanUp()

    def test_10_action_add_to_playlist(self):
        """
        Test adding a folder to a playlist
        """
        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)

        folder = self.FolderObj.search([("path", "like", "Album1")])
        playlist = self.PlaylistObj.search([("current", "=", True)], limit=1)

        # Check data prior any action
        self.assertEqual(len(folder), 1)
        self.assertEqual(len(playlist), 1)

        # Add folder
        folder.action_add_to_playlist()
        self.assertEqual(
            playlist.mapped("playlist_line_ids").mapped("track_id").mapped("name"),
            [u"Song1", u"Song2"],
        )

        self.cleanUp()

    def test_20_oomusic_browse(self):
        """
        Test oomusic_browse method
        """
        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)

        folder1 = self.FolderObj.search([("path", "=like", "%Artist1")])
        folder2 = self.FolderObj.search([("path", "=like", "%Album1")])
        playlist = self.PlaylistObj.search([("current", "=", True)], limit=1)

        # Check data prior any action
        self.assertEqual(len(folder1 + folder2), 2)
        self.assertEqual(len(playlist), 1)

        # Browse folders
        res1 = json.loads(folder1.oomusic_browse())
        res2 = json.loads(folder2.oomusic_browse())
        self.assertEqual(res1["current_id"]["name"], folder1.path)
        self.assertEqual(res1["parent_id"]["name"], "Artist1")
        self.assertEqual(len(res1["child_ids"]), 2)
        self.assertEqual(len(res1["track_ids"]), 0)
        self.assertEqual(res2["current_id"]["name"], folder2.path)
        self.assertEqual(res2["parent_id"]["name"], "Album1")
        self.assertEqual(len(res2["child_ids"]), 0)
        self.assertEqual(len(res2["track_ids"]), 2)

        self.cleanUp()
