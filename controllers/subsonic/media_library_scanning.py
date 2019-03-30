# -*- coding: utf-8 -*-

from lxml import etree

from odoo import http
from odoo.http import request
from .common import SubsonicREST


class MusicSubsonicMediaLibraryScanning(http.Controller):
    @http.route(
        ["/rest/getScanStatus.view"],
        type="http",
        auth="public",
        csrf=False,
        methods=["GET", "POST"],
    )
    def getScanStatus(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        folders = request.env["oomusic.folder"].search([("root", "=", True)])

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        xml_status = rest.make_ScanStatus(folders)
        root.append(xml_status)

        return rest.make_response(root)

    @http.route(
        ["/rest/startScan.view"], type="http", auth="public", csrf=False, methods=["GET", "POST"]
    )
    def startScan(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        folders = request.env["oomusic.folder"].search([("root", "=", True)])
        for folder in folders:
            folder.action_scan_folder()

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        xml_status = rest.make_ScanStatus(folders, scan=True)
        root.append(xml_status)

        return rest.make_response(root)
