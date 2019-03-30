# -*- coding: utf-8 -*-

from . import test_common


class TestOomusicAlbum(test_common.TestOomusicCommon):
    def test_00_action_add_to_playlist(self):
        """
        Test adding an album to a playlist
        """
        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)

        album1 = self.AlbumObj.search([("name", "=", "Album1")])
        album2 = self.AlbumObj.search([("name", "=", "Album2")])
        playlist = self.PlaylistObj.search([("current", "=", True)], limit=1)

        # Check data prior any action
        self.assertEqual(len(album1), 1)
        self.assertEqual(len(album2), 1)
        self.assertEqual(len(playlist), 1)

        # Add Album1
        album1.action_add_to_playlist()
        self.assertEqual(
            playlist.mapped("playlist_line_ids").mapped("track_id").mapped("name"),
            [u"Song1", u"Song2"],
        )

        # Check no duplicate is created
        album1.action_add_to_playlist()
        self.assertEqual(
            playlist.mapped("playlist_line_ids").mapped("track_id").mapped("name"),
            [u"Song1", u"Song2"],
        )

        # Purge and replace by Album2
        album2.with_context(purge=True).action_add_to_playlist()
        self.assertEqual(
            playlist.mapped("playlist_line_ids").mapped("track_id").mapped("name"),
            [u"Song3", u"Song4"],
        )

        self.cleanUp()
