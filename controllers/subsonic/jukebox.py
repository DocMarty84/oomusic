# -*- coding: utf-8 -*-

from odoo import http
from common import SubsonicREST

class MusicSubsonicJukebox(http.Controller):
    @http.route(['/rest/jukeboxControl.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def jukeboxControl(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        return rest.make_error(code='30', message='Feature not supported by server.')
