# -*- coding: utf-8 -*-

from lxml import etree

from odoo import http

from .common import SubsonicREST


class MusicSubsonicShare(http.Controller):
    @http.route(
        ["/rest/getShares.view"], type="http", auth="public", csrf=False, methods=["GET", "POST"]
    )
    def getShares(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        xml_shares = rest.make_Shares()
        root.append(xml_shares)

        # TODO support shares

        return rest.make_response(root)

    @http.route(
        ["/rest/createShare.view"], type="http", auth="public", csrf=False, methods=["GET", "POST"]
    )
    def createShare(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        return rest.make_error(code="30", message="Feature not supported by server.")

    @http.route(
        ["/rest/updateShare.view"], type="http", auth="public", csrf=False, methods=["GET", "POST"]
    )
    def updateShare(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        return rest.make_response(root)

    @http.route(
        ["/rest/deleteShare.view"], type="http", auth="public", csrf=False, methods=["GET", "POST"]
    )
    def deleteShare(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        return rest.make_response(root)
