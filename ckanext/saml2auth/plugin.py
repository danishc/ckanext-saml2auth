"""
Copyright (c) 2020 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

# encoding: utf-8
import logging

from saml2.client_base import LogoutError

from flask import session

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import g

from ckanext.saml2auth.views.saml2auth import saml2auth
from ckanext.saml2auth.cache import get_subject_id, get_saml_session_info
from ckanext.saml2auth.spconfig import get_config as sp_config
from ckanext.saml2auth import helpers as h


log = logging.getLogger(__name__)


class Saml2AuthPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IAuthenticator)

    # ITemplateHelpers

    def get_helpers(self):
        return {
            'is_default_login_enabled':
                h.is_default_login_enabled
        }

    # IConfigurable

    def configure(self, config):
        # Certain config options must exists for the plugin to work. Raise an
        # exception if they're missing.
        missing_config = "{0} is not configured. Please amend your .ini file."
        config_options = (
            'ckanext.saml2auth.user_email',
        )
        if not config.get('ckanext.saml2auth.idp_metadata.local_path'):
            config_options += ('ckanext.saml2auth.idp_metadata.remote_url',)
        for option in config_options:
            if not config.get(option, None):
                raise RuntimeError(missing_config.format(option))

        first_and_last_name = all((
            config.get('ckanext.saml2auth.user_firstname'),
            config.get('ckanext.saml2auth.user_lastname')
        ))
        full_name = config.get('ckanext.saml2auth.user_fullname')

        if not first_and_last_name and not full_name:
            raise RuntimeError('''You need to provide both ckanext.saml2auth.user_firstname
            + ckanext.saml2auth.user_lastname or ckanext.saml2auth.user_fullname'''.strip())

        acs_endpoint = config.get('ckanext.saml2auth.acs_endpoint')
        if acs_endpoint and not acs_endpoint.startswith('/'):
            raise RuntimeError('ckanext.saml2auth.acs_endpoint should start with a slash ("/")')

    # IBlueprint

    def get_blueprint(self):
        return [saml2auth]

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'saml2auth')

    # IAuthenticator

    def identify(self):
        pass

    def login(self):
        pass

    def logout(self):

        # We need to logout from IDP as well
        client = h.saml_client(
            sp_config()
        )
        saml_session_info = get_saml_session_info(session)
        subject_id = get_subject_id(session)
        client.users.add_information_about_person(saml_session_info)

        if subject_id is None:
            log.warning(
                'The session does not contain the subject id for user %s', g.user)

        try:
            result = client.global_logout(name_id=subject_id)
            print(result)
        except LogoutError as e:
            log.exception(
                'Error Handled - SLO not supported by IDP: {}'.format(e))
            # clear session

        if not result:
            log.error(
                "Looks like the user {} is not logged in any IdP/AA".format(subject_id))

        if len(result) > 1:
            log.error(
                'Sorry, I do not know how to logout from several sources.'
                ' I will logout just from the first one')
