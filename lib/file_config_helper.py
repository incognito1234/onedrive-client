#  Copyright 2019-2024 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
import logging
import os
import sys
import stat

lg = logging.getLogger('odc.config')


def create_and_get_config_folder():
  if 'HOME' in os.environ:
    home_folder = os.environ['HOME']
  elif 'APPDATA' in os.environ:
    home_folder = os.environ['APPDATA']
  else:
    home_folder = ''
  param_folder = f"{home_folder}/.odc/"

  if not os.path.exists(param_folder):
    try:
      os.makedirs(param_folder)
      os.chmod(param_folder, mode=stat.S_IXUSR | stat.S_IWUSR | stat.S_IRUSR)
      result = param_folder
    except BaseException:
      lg.error("Error will creation of config folder")
      result = None
  else:
    result = param_folder
  return result


def force_permission_file_read_write_owner(filename):
  try:
    os.chmod(filename, stat.S_IWUSR | stat.S_IRUSR)
  except BaseException:
    lg.error("Error will setting permission of token")
