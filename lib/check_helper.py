#  Copyright 2019-2023 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
import base64
import subprocess
import os
from shutil import which

try:
  import quickxorhash as qxh
except ImportError:
  qxh = None


class quickxorhash:

  __COMMAND_NAME = 'quickxorhash'

  def __init__(self):
    self.program = which(self.__COMMAND_NAME)

  def quickxorhash(self, filename):
    if qxh is not None:
      h = qxh.quickxorhash()
      h.update(open(filename, 'rb').read())
      return base64.b64encode(h.digest()).decode('utf8')

    if self.program is not None:
      p = subprocess.run([self.program, filename], stdout=subprocess.PIPE)
      if p.returncode != 0:
        return None
      else:
        return str(p.stdout, 'utf-8')[:-1]
    else:
      return None

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
