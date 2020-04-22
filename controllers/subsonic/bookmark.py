# -*- coding: utf-8 -*-

from lxml import etree

from odoo import http

from .common import SubsonicREST


class MusicSubsonicBookmarks(http.Controller):
    @http.route(
        ["/rest/getBookmarks.view", "/rest/getBookmarks"],
        type="http",
        auth="public",
        csrf=False,
        methods=["GET", "POST"],
    )
    def getBookmarks(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        xml_bookmarks = rest.make_Bookmarks()
        root.append(xml_bookmarks)

        return rest.make_response(root)

    @http.route(
        [
            "/rest/createBookmark.view",
            "/rest/createBookmark",
            "/rest/deleteBookmark.view",
            "/rest/deleteBookmark",
            "/rest/getPlayQueue.view",
            "/rest/getPlayQueue",
            "/rest/savePlayQueue.view",
            "/rest/savePlayQueue",
        ],
        type="http",
        auth="public",
        csrf=False,
        methods=["GET", "POST"],
    )
    def actionBookmark(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)

        return rest.make_response(root)
