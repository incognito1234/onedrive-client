import subprocess
import os


class quickxorhash:

  __COMMAND_NAME = 'quickxorhash'

  def __init__(self):
    list_folder = where(quickxorhash.__COMMAND_NAME)
    if len(list_folder) != 1:
      print('pbm')
      self.program = None
    else:
      self.program = "{0}".format(list_folder[0])

  def quickxorhash(self, filename):

    if self.program is not None:
      p = subprocess.run([self.program, filename], capture_output=True)
      if p.returncode != 0:
        return None
      else:
        return str(p.stdout, 'utf-8')[:-1]
    else:
      return None


def where(name, flags=os.F_OK):
    #
    # 18/10/2020
    # From: https://codereview.stackexchange.com/questions/123597/find-a-specific-file-or-find-all-executable-files-within-the-system-path
    #
  result = []
  paths = os.defpath.split(os.pathsep)
  for outerpath in paths:
    for innerpath, _, _ in os.walk(outerpath):
      path = os.path.join(innerpath, name)
      if os.access(path, flags):
        result.append(os.path.normpath(path))
  return result

  # How to get quickxorhash command
  #
  # git clone https://github.com/sndr-oss/quickxorhash-c.git
  #
  # apt install pkg-config libtool automake
  # autoreconf -i
  # ./configure
  # make
  #
  # -- installation ---
  # make install
  #
  # -- update cache of libraries from /etc/ld.so.conf
  # ldconfig
  #
  # -- uninstallation --
  # git clean -dfX
