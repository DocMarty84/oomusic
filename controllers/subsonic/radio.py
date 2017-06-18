# -*- coding: utf-8 -*-

from lxml import etree

from odoo import http
from common import SubsonicREST


class MusicSubsonicRadio(http.Controller):
    @http.route(['/rest/getInternetRadioStations.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getInternetRadioStations(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_radios = rest.make_InternetRadioStations()
        root.append(xml_radios)

        return rest.make_response(root)
