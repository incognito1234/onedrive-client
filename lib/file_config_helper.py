import os
import sys
import stat
from lib.log import Logger


def create_and_get_config_folder(lg: Logger = None):
  if 'HOME' in os.environ:
    home_folder = os.environ['HOME']
  elif 'APPDATA' in os.environ:
    home_folder = os.environ['APPDATA']
  else:
    home_folder = ''
  param_folder = "{}/.odc/".format(home_folder)

  if not os.path.exists(param_folder):
    try:
      os.makedirs(param_folder)
      os.chmod(param_folder, mode=stat.S_IXUSR | stat.S_IWUSR | stat.S_IRUSR)
      result = param_folder
    except BaseException:
      if lg is not None:
        lg.log_error("Error will creation of config folder")
      else:
        print("Error will creation of config folder", file=sys.stderr)

      result = None
  else:
    result = param_folder
  return result


def force_permission_file_read_write_owner(filename, lg: Logger = None):
  try:
    os.chmod(filename, stat.S_IWUSR | stat.S_IRUSR)
  except BaseException:
    if lg is not None:
      lg.log_error("Error will setting permission of token")
    else:
      print("Error will setting permission of token", file=sys.stderr)
