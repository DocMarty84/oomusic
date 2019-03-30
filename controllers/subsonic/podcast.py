# -*- coding: utf-8 -*-

from lxml import etree

from odoo import http
from .common import SubsonicREST


class MusicSubsonicPodcast(http.Controller):
    @http.route(
        ["/rest/getPodcasts.view"], type="http", auth="public", csrf=False, methods=["GET", "POST"]
    )
    def getPodcasts(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        xml_podcasts = rest.make_Podcasts()
        root.append(xml_podcasts)

        return rest.make_response(root)

    @http.route(
        ["/rest/getNewestPodcasts.view"],
        type="http",
        auth="public",
        csrf=False,
        methods=["GET", "POST"],
    )
    def getNewestPodcasts(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        xml_podcasts = rest.make_Podcasts(tag_name="newestPodcasts")
        root.append(xml_podcasts)

        return rest.make_response(root)

    @http.route(
        [
            "/rest/refreshPodcasts.view",
            "/rest/createPodcastChannel.view",
            "/rest/deletePodcastChannel.view",
            "/rest/deletePodcastEpisode.view",
            "/rest/downloadPodcastEpisode.view",
        ],
        type="http",
        auth="public",
        csrf=False,
        methods=["GET", "POST"],
    )
    def actionPodcasts(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        return rest.make_response(root)
