# -*- coding: utf-8 -*-

import logging
import os

from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MusicController(http.Controller):

    @http.route(['/oomusic/down/<int:track_id>'], type='http', auth='user')
    def down(self, track_id, **kwargs):
        Track = request.env['oomusic.track'].browse([track_id])
        return http.send_file(Track.path, as_attachment=True)

    @http.route([
        '/oomusic/trans/<int:track_id>.<string:output_format>',
        ], type='http', auth='user')
    def trans(self, track_id, output_format, **kwargs):
        Track = request.env['oomusic.track'].browse([track_id])
        fn_ext = os.path.splitext(Track.path)[1]

        # Get kwargs
        seek = int(kwargs.get('seek', 0))
        norm = int(kwargs.get('norm', 0))
        raw = int(kwargs.get('raw', 0))

        # Stream the file.
        # - if raw is activated and the file is not seeked, simply send the file
        # - if raw is activated and the file is seeked, use a specific transcoder
        # - In other cases, search for an appropriate transcoder
        if raw and not seek:
            return http.send_file(Track.path)
        elif raw and seek:
            Transcoder = request.env.ref('oomusic.oomusic_transcoder_99')
        else:
            Transcoder = request.env['oomusic.transcoder'].search([
                ('output_format.name', '=', output_format)
            ]).filtered(lambda r: fn_ext[1:] not in r.mapped('black_formats').mapped('name'))
        Transcoder = Transcoder[0] if Transcoder else False

        if Transcoder:
            generator = Transcoder.transcode(track_id, seek=seek, norm=norm).stdout
            mimetype = Transcoder.output_format.mimetype
        else:
            _logger.warning('Could not find converter from "%s" to "%s"', fn_ext[1:], output_format)
            return http.send_file(Track.path)

        # FIXME: see http://librelist.com/browser/flask/2011/10/5/response-to-a-range-request/#1e95dd715f412161d3db2fc8aaf8666f

        # Set a buffer size of 200 KB. The default value (8 KB) seems too small and leads to chunk
        # download errors. Since the player is not fault-tolerant, a single download error leads to
        # a complete stop of the music. Maybe consider this value as a user option for people with
        # bad network.
        data = wrap_file(
            request.httprequest.environ, generator, buffer_size=Transcoder.buffer_size * 1024)
        return Response(data, mimetype=mimetype, direct_passthrough=True)
