# -*- coding: utf-8 -*-

import shutil
import os

from odoo.api import Environment
from odoo.tests import common


class TestOomusicSubCommon(common.HttpCase):

    def setUp(self):
        super(TestOomusicSubCommon, self).setUp()
        login = passw = 'admin'
        self.authenticate(login, passw)
        self.cred = '?u={}&p={}&v=1.16.0'.format(login, passw)

        cr = self.registry.cursor()
        self.env2 = env = Environment(cr, self.uid, {})
        self.AlbumObj = env['oomusic.album']
        self.ArtistObj = env['oomusic.artist']
        self.ConverterObj = env['oomusic.converter']
        self.FolderScanObj = env['oomusic.folder.scan']
        self.FolderObj = env['oomusic.folder']
        self.GenreObj = env['oomusic.genre']
        self.PlaylistLineObj = env['oomusic.playlist.line']
        self.PlaylistObj = env['oomusic.playlist']
        self.TrackObj = env['oomusic.track']

        self.cleanUp()
        shutil.copytree(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'folder_scan'),
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'folder_scan_test')
        )
        self.Folder = self.env2['oomusic.folder'].create({
            'path': os.path.join(os.path.dirname(os.path.realpath(__file__)), 'folder_scan_test')
        })
        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)

    def cleanUp(self):
        shutil.rmtree(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'folder_scan_test'), True
        )
