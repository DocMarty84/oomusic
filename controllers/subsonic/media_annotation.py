# -*- coding: utf-8 -*-

from lxml import etree

from odoo import http
from odoo.http import request
from .common import SubsonicREST


class MusicSubsonicMediaAnnotation(http.Controller):
    @http.route(
        ["/rest/star.view"], type="http", auth="public", csrf=False, methods=["GET", "POST"]
    )
    def star(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        trackId = kwargs.get("id")
        if trackId:
            track = request.env["oomusic.track"].browse([int(trackId)])
            if track.exists():
                track.write({"star": "1"})
            else:
                folder = request.env["oomusic.folder"].browse([int(trackId)])
                if folder.exists():
                    folder.write({"star": "1"})

        albumId = kwargs.get("albumId")
        if albumId:
            album = request.env["oomusic.album"].browse([int(albumId)])
            if album.exists():
                album.write({"star": "1"})

        artistId = kwargs.get("artistId")
        if artistId:
            artist = request.env["oomusic.artist"].browse([int(artistId)])
            if artist.exists():
                artist.write({"star": "1"})

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)

        return rest.make_response(root)

    @http.route(
        ["/rest/unstar.view"], type="http", auth="public", csrf=False, methods=["GET", "POST"]
    )
    def unstar(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        trackId = kwargs.get("id")
        if trackId:
            track = request.env["oomusic.track"].browse([int(trackId)])
            if track.exists():
                track.write({"star": "0"})
            else:
                folder = request.env["oomusic.folder"].browse([int(trackId)])
                if folder.exists():
                    folder.write({"star": "1"})

        albumId = kwargs.get("albumId")
        if albumId:
            album = request.env["oomusic.album"].browse([int(albumId)])
            if album.exists():
                album.write({"star": "0"})

        artistId = kwargs.get("artistId")
        if artistId:
            artist = request.env["oomusic.artist"].browse([int(artistId)])
            if artist.exists():
                artist.write({"star": "0"})

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)

        return rest.make_response(root)

    @http.route(
        ["/rest/setRating.view"], type="http", auth="public", csrf=False, methods=["GET", "POST"]
    )
    def setRating(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        rating = kwargs.get("rating")
        if rating is None:
            return rest.make_error(
                code="10", message='Required string parameter "rating" is not present'
            )

        Id = kwargs.get("id")
        if Id:
            found = False

            # Subsonic seems to have shared ids between tracks, albums and folders. Therefore, we
            # never know what the user wants to rate when the route is called.
            album = request.env["oomusic.album"].browse([int(Id)])
            if album.exists():
                album.write({"rating": rating})
                found = True
            if not found:
                track = request.env["oomusic.track"].browse([int(Id)])
                if track.exists():
                    track.write({"rating": rating})
                    found = True
            if not found:
                folder = request.env["oomusic.folder"].browse([int(Id)])
                if folder.exists():
                    folder.write({"rating": rating})
        else:
            return rest.make_error(code="10", message='Required int parameter "id" is not present')

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)

        return rest.make_response(root)

    @http.route(
        ["/rest/scrobble.view"], type="http", auth="public", csrf=False, methods=["GET", "POST"]
    )
    def scrobble(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        # TODO support lastfm scrobble

        return rest.make_error(code="30", message="Feature not supported by server.")
