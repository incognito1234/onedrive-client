
import yaml
from requests_oauthlib import OAuth2Session
import os
import time
import json

# This is necessary for testing with non-HTTPS localhost
# Remove this if deploying to production
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# This is necessary because Azure does not guarantee
# to return scopes in the same case and order as requested
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
os.environ['OAUTHLIB_IGNORE_SCOPE_CHANGE'] = '1'

# Load the oauth_settings.yml file
current_dirname = os.path.dirname(os.path.realpath(__file__))
stream = open("{0}/../oauth_settings.yml".format(current_dirname), 'r')
settings = yaml.load(stream, yaml.SafeLoader)
authorize_url = '{0}{1}'.format(
    settings['authority'],
    settings['authorize_endpoint'])
token_url = '{0}{1}'.format(settings['authority'], settings['token_endpoint'])

# Method to generate a sign-in url


def get_sign_in_url():
  # Initialize the OAuth client
  aad_auth = OAuth2Session(settings['app_id'],
                           scope=settings['scopes'],
                           redirect_uri=settings['redirect'])

  sign_in_url, state = aad_auth.authorization_url(
      authorize_url, prompt='login')

  return sign_in_url, state

# Method to exchange auth code for access token


def get_token_from_code(callback_url, expected_state):
  # Initialize the OAuth client
  aad_auth = OAuth2Session(settings['app_id'],
                           state=expected_state,
                           scope=settings['scopes'],
                           redirect_uri=settings['redirect'])

  token = aad_auth.fetch_token(token_url,
                               client_secret=settings['app_secret'],
                               authorization_response=callback_url)

  return token


class TokenRecorder:

  """ Class that permits to store Azure
  """

  def __init__(self, filename):
    self.filename = filename
    self.token = None
    self.logger = Logger(None, 4)

  def __init__(self, filename, logger):
    self.filename = filename
    self.token = None
    self.logger = logger

  def store_token(self, token):
    """
        Record token
    """
    with open(self.filename, 'w') as tokenfile:
      json.dump(token, tokenfile)
      self.token = token
    return 1

  def __refresh_token(self, token):
    self.logger.log_info("Refresh token")
    self.store_token(token)

  def token_exists(self):
    try:
      with open(self.filename, 'r') as tokenfile:
        data = json.load(tokenfile)
        self.token = data
        result = 1
    except Exception as err:
      self.logger.log_error(
          "Error during loading of file {0} - {1}".format(self.filename, err))
      result = 0

    return result

  def get_token(self):
    if self.token is not None:
      # Check expiration
      now = time.time()
      # Subtract 5 minutes from expiration to account for clock skew
      expire_time = self.token['expires_at'] - 300
      if now >= expire_time:
        # Refresh the token
        aad_auth = OAuth2Session(settings['app_id'],
                                 token=self.token,
                                 scope=settings['scopes'],
                                 redirect_uri=settings['redirect'])

        refresh_params = {
            'client_id': settings['app_id'],
            'client_secret': settings['app_secret'],
        }
        new_token = aad_auth.refresh_token(token_url, **refresh_params)

        # Save new token
        self.store_token(new_token)

        # Return new access token (that has just been stored)
        return self.token

      else:
        # Token still valid, just return it
        return self.token

    else:
      return None

  def get_session_from_token(self):
    self.logger.log_debug("Get session from token starting")
    refresh_params = {
        'client_id': settings['app_id'],
        'client_secret': settings['app_secret'],
    }
    client = OAuth2Session(settings['app_id'],
                           token=self.token,
                           scope=settings['scopes'],
                           redirect_uri=settings['redirect'],
                           auto_refresh_url=token_url,
                           auto_refresh_kwargs=refresh_params,
                           token_updater=self.__refresh_token)
    return client
