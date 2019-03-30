# -*- coding: utf-8 -*-

from lxml import etree

from odoo import http
from .common import SubsonicREST


class MusicSubsonicChat(http.Controller):
    @http.route(
        ["/rest/getChatMessages.view"],
        type="http",
        auth="public",
        csrf=False,
        methods=["GET", "POST"],
    )
    def getChatMessages(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        xml_messages = rest.make_ChatMessages()
        root.append(xml_messages)

        return rest.make_response(root)

    @http.route(
        ["/rest/addChatMessage.view"],
        type="http",
        auth="public",
        csrf=False,
        methods=["GET", "POST"],
    )
    def addChatMessage(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)

        return rest.make_response(root)
