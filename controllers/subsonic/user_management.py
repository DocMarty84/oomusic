# -*- coding: utf-8 -*-

from lxml import etree

from odoo import http
from odoo.http import request
from common import SubsonicREST


class MusicSubsonicUserManagement(http.Controller):
    @http.route(['/rest/getUser.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getUser(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        username = kwargs.get('username')
        if not username:
            return rest.make_error(
                code='10', message='Required string parameter "username" is not present'
            )

        user = request.env['res.users'].search([('login', '=', username)])
        if not user:
            return rest.make_error(code='70', message='User not found')

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_user = rest.make_User(user)
        root.append(xml_user)

        return rest.make_response(root)

    @http.route(['/rest/getUsers.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getUsers(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)
        xml_users = rest.make_Users()
        root.append(xml_users)

        users = request.env['res.users'].search([])
        for user in users:
            xml_user = rest.make_User(user)
            xml_users.append(xml_user)

        return rest.make_response(root)

    @http.route([
        '/rest/createUser.view', '/rest/updateUser.view',
        '/rest/deleteUser.view', '/rest/changePassword.view'
        ], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def actionUsers(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        # Do not support these actions on purpose, for security reason

        root = etree.Element('subsonic-response', status='ok', version=rest.version_server)

        return rest.make_response(root)
