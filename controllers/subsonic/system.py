# -*- coding: utf-8 -*-

from lxml import etree

from odoo import http
from common import SubsonicREST


class MusicSubsonicSystem(http.Controller):
    @http.route(['/rest/ping.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def ping(self, **kwargs):
        rest = SubsonicREST(kwargs)
        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        return rest.make_response(root)

    @http.route(['/rest/getLicense.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getLicense(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        etree.SubElement(
            root, 'license', valid='true', email='foo@bar.com', licenseExpires='2099-12-31T23:59:59'
        )
        return rest.make_response(root)
