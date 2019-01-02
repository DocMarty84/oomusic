# -*- coding: utf-8 -*-

import shutil
import os

from odoo.tests import common


class TestOomusicCommon(common.TransactionCase):

    def setUp(self):
        super(TestOomusicCommon, self).setUp()

        self.AlbumObj = self.env['oomusic.album']
        self.ArtistObj = self.env['oomusic.artist']
        self.ConverterObj = self.env['oomusic.converter']
        self.FolderScanObj = self.env['oomusic.folder.scan']
        self.FolderObj = self.env['oomusic.folder']
        self.GenreObj = self.env['oomusic.genre']
        self.PlaylistLineObj = self.env['oomusic.playlist.line']
        self.PlaylistObj = self.env['oomusic.playlist']
        self.TrackObj = self.env['oomusic.track']

        self.cleanUp()
        shutil.copytree(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'folder_scan'),
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'folder_scan_test')
        )
        self.Folder = self.FolderObj.create({
            'path': os.path.join(os.path.dirname(os.path.realpath(__file__)), 'folder_scan_test')
        })

    def cleanUp(self):
        shutil.rmtree(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'folder_scan_test'), True
        )
