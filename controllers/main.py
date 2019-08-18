# -*- coding: utf-8 -*-

import logging
import os

from werkzeug.exceptions import abort, Forbidden
from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file

from odoo import http, fields, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class MusicController(http.Controller):
    @http.route(["/oomusic/down"], auth="public", type="http")
    def down(self, **kwargs):
        down = (
            request.env["oomusic.download"]
            .sudo()
            .search(
                [
                    ("access_token", "=", kwargs["token"]),
                    ("expiration_date", ">=", fields.Date.today()),
                ],
                limit=1,
            )
        )
        if not down:
            abort(404)

        # Set a minimum delay between link access to avoid overload
        now = fields.Datetime.now()
        if down.access_date and (now - down.access_date).seconds < down.min_delay:
            raise Forbidden(_("Too many requests received. Please try again in a few minutes."))
        down._update_access_date(now)

        # Get the ZIP file
        obj_sudo = request.env[down.res_model].sudo().browse(down.res_id)
        tracks = obj_sudo._get_track_ids()
        return http.send_file(
            tracks._build_zip(flatten=down.flatten, name=kwargs["token"]), as_attachment=True
        )

    @http.route(["/oomusic/down_user"], auth="user", type="http")
    def down_user(self, **kwargs):
        obj = request.env[kwargs["model"]].browse(int(kwargs["id"]))
        if not obj.exists():
            abort(404)
        tracks = obj._get_track_ids()
        flatten = bool(int(kwargs.get("flatten", "0")))
        return http.send_file(tracks._build_zip(flatten=flatten), as_attachment=True)

    @http.route(["/oomusic/trans/<int:track_id>.<string:output_format>"], type="http", auth="user")
    def trans(self, track_id, output_format, **kwargs):
        Track = request.env["oomusic.track"].browse([track_id])
        fn_ext = os.path.splitext(Track.path)[1]

        # Get kwargs
        seek = int(kwargs.get("seek", 0))
        mode = kwargs.get("mode", "standard")

        # Stream the file.
        # - if raw is activated and the file is not seeked, simply send the file
        # - if raw is activated and the file is seeked, use a specific transcoder
        # - In other cases, search for an appropriate transcoder
        if mode == "raw" and not seek:
            return http.send_file(Track.path)
        elif mode == "raw" and seek:
            Transcoder = request.env.ref("oomusic.oomusic_transcoder_99")
        else:
            Transcoder = (
                request.env["oomusic.transcoder"]
                .search([("output_format.name", "=", output_format)])
                .filtered(lambda r: fn_ext[1:] not in r.mapped("black_formats.name"))
            )
        Transcoder = Transcoder[0] if Transcoder else False

        if Transcoder:
            generator = Transcoder.transcode(
                track_id, seek=seek, norm=True if mode == "norm" else False
            ).stdout
            mimetype = Transcoder.output_format.mimetype
        else:
            _logger.warning("Could not find converter from '%s' to '%s'", fn_ext[1:], output_format)
            return http.send_file(Track.path)

        # FIXME: see http://librelist.com/browser/flask/2011/10/5/response-to-a-range-request/#1e95dd715f412161d3db2fc8aaf8666f

        # Set a buffer size of 200 KB. The default value (8 KB) seems too small and leads to chunk
        # download errors. Since the player is not fault-tolerant, a single download error leads to
        # a complete stop of the music. Maybe consider this value as a user option for people with
        # bad network.
        data = wrap_file(
            request.httprequest.environ, generator, buffer_size=Transcoder.buffer_size * 1024
        )
        return Response(data, mimetype=mimetype, direct_passthrough=True)
