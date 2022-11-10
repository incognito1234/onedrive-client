#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details

import logging
import yaml
from requests_oauthlib import OAuth2Session
import os
import time
import json
import msal
import urllib.parse

lg = logging.getLogger('odc.auth')

# This is necessary for testing with non-HTTPS localhost
# Remove this if deploying to production
# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# This is necessary because Azure does not guarantee
# to return scopes in the same case and order as requested
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
os.environ['OAUTHLIB_IGNORE_SCOPE_CHANGE'] = '1'

# Load the oauth_settings.yml file
current_dirname = os.path.dirname(os.path.realpath(__file__))
stream = open(f"{current_dirname}/../oauth_settings.yml", 'r')
settings = yaml.load(stream, yaml.SafeLoader)
stream.close()
authorize_url = f"{settings['authority']}{settings['authorize_endpoint']}"
token_url = f"{settings['authority']}{settings['token_endpoint']}"
redirect_url = settings['redirect']
scopes_app = settings['scopes'].split()

# Method to generate a sign-in url


class TokenRecorder:

  """ Class that permits to store Azure
  """

  def __init__(self, filename):
    self.filename = filename
    self.token = None
    self.__cache = None

  def get_token_interactivaly(self, prefix_url, prompt_url_callback):
    # Initialize the OAuth client
    self.__cache = msal.SerializableTokenCache()
    app = msal.ConfidentialClientApplication(
        settings['app_id'],
        authority=settings['authority'],
        client_credential=settings['app_secret'],
        token_cache=self.__cache)

    dict_auth = app.initiate_auth_code_flow(
        scopes=scopes_app, redirect_uri=redirect_url)
    print(f"{prefix_url}{dict_auth['auth_uri']}")
    resp = input(prompt_url_callback)

    try:
      if len(resp) > len(redirect_url):
        resp = resp[(len(redirect_url) + 1):]  # +1 to consume the char "?"
      print(f"resp={resp}")
      dict_resp = urllib.parse.parse_qs(resp)
    except Exception as e:
      lg.error(f"Error during parsing of callback url - {e}")
      return False
    for key_dict in dict_resp:
      dict_resp[key_dict] = dict_resp[key_dict][0]

    result = app.acquire_token_by_auth_code_flow(
        auth_code_flow=dict_auth, auth_response=dict_resp)

    return "access_token" in result

  def store_token(self):
    if self.__cache is not None and self.__cache.has_state_changed:
      lg.debug(f"[store_token]Store in file {self.filename}")
      open(self.filename, 'w').write(self.__cache.serialize())
    else:
      lg.error("[store_token]No need to store token")

  def __refresh_token(self, token):
    lg.debug("Refresh token")
    self.init_token_from_file()
    self.store_token()

  def token_exists(self):
    return self.token is not None

  def init_token_from_file(self):
    lg.debug("Init token from file")
    try:
      self.__cache = msal.SerializableTokenCache()
      if os.path.exists(self.filename):
        with open(self.filename, "r") as f:
          self.__cache.deserialize(f.read())
      app = msal.ConfidentialClientApplication(
          settings['app_id'],
          authority=settings['authority'],
          client_credential=settings['app_secret'],
          token_cache=self.__cache)
      accounts = app.get_accounts()
      chosen = accounts[0]
      self.token = app.acquire_token_silent(scopes_app, account=chosen)

    except Exception as err:
      lg.warn(f"Error during file loading {self.filename} - {err}")

  def get_session_from_token(self):
    lg.debug("Get session from token starting")
    refresh_params = {
        'client_id': settings['app_id'],
        'client_secret': settings['app_secret'],
    }
    client = OAuth2Session(
        settings['app_id'],
        token=self.token,
        scope=settings['scopes'],
        redirect_uri=settings['redirect'],
        auto_refresh_url=token_url,
        auto_refresh_kwargs=refresh_params,
        token_updater=self.__refresh_token)
    return client
