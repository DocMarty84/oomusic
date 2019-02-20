# -*- coding: utf-8 -*-

import shutil
import os

from odoo import fields
from odoo.tests import common


def _dt_to_string(dt):
    dt_string = fields.Datetime.to_string(dt)
    return dt_string.replace(' ', 'T') + 'Z'


class TestOomusicSubCommon(common.HttpCase):

    def setUp(self):
        super(TestOomusicSubCommon, self).setUp()
        login = passw = 'admin'
        self.cred = '?u={}&p={}&v=1.16.1'.format(login, passw)

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
        self.Folder = self.env['oomusic.folder'].create({
            'path': os.path.join(os.path.dirname(os.path.realpath(__file__)), 'folder_scan_test'),
            'user_id': self.env['res.users'].search([('login', '=', 'admin')], limit=1).id,
        })
        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)

    def cleanUp(self):
        shutil.rmtree(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'folder_scan_test'), True
        )
