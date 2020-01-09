# -*- coding: utf-8 -*-

import logging

import werkzeug.utils
from werkzeug.exceptions import abort

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MusicRemote(http.Controller):
    @http.route(
        [
            "/oomusic/remote/<string:access_token>",
            "/oomusic/remote/<string:access_token>/<string:control>",
        ],
        auth="user",
        type="http",
    )
    def remote(self, access_token, control=False, **kwargs):
        remote = request.env["oomusic.remote"].search(
            [("access_token", "=", access_token), ("public", "=", False)]
        )
        return self._render_remote(remote, access_token, control)

    @http.route(
        [
            "/oomusic/remote_public/<string:access_token>",
            "/oomusic/remote_public/<string:access_token>/<string:control>",
        ],
        auth="public",
        type="http",
    )
    def remote_public(self, access_token, control=False, **kwargs):
        remote = (
            request.env["oomusic.remote"]
            .sudo()
            .search([("access_token", "=", access_token), ("public", "=", True)])
        )
        return self._render_remote(remote, access_token, control)

    def _render_remote(self, remote, access_token, control=False):
        if not remote:
            _logger.warn("Access refused with token %s", access_token)
            abort(404)
        _logger.info("Access granted with token %s, control: %s", access_token, control)
        if control:
            notification = {"control": control}
            request.env["bus.bus"].sendone(
                (request.db, "oomusic.remote", remote.user_id.id), notification
            )
            return werkzeug.utils.redirect(remote.url)
        line = (
            request.env["oomusic.playlist.line"]
            .with_user(remote.user_id)
            .search([("playing", "=", True)], limit=1)
        )
        return request.render(
            "oomusic.remote", {"url": remote.url, "public": remote.public, "line": line}
        )
