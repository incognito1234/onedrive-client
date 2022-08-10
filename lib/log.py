#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
"""
    Log module
"""

import datetime


class Logger:
  """
      Logger class
  """

  LOG_LEVEL_DEBUG = 4
  LOG_LEVEL_INFO = 3
  LOG_LEVEL_WARNING = 2
  LOG_LEVEL_ERROR = 1
  LOG_LEVEL_NONE = 0

  def __init__(self, filename, loglevel, with_stdout=False):
    self.filename = filename
    if loglevel is None:
      self.loglevel = 0
    else:
      self.loglevel = loglevel
    self.with_stdout = with_stdout

  def log(self, what, level):
    """
        Log something according to level
    """
    if self.filename is None and not self.with_stdout:
      return 0

    if level <= self.loglevel:
      fts_loglevel = (
          "NONE",
          "ERROR",
          "WARNING",
          "INFO",
          "DEBUG")  # formats loglevel

      tobelogged = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
      tobelogged += " - " + fts_loglevel[level]
      tobelogged += " - " + what

      if self.filename is not None:
        F = open(self.filename, "a")
        F.write(tobelogged + "\n")
        F.close()
      if self.with_stdout:
        print(tobelogged)
    return 1

  def log_debug(self, what):
    self.log(what, Logger.LOG_LEVEL_DEBUG)

  def log_info(self, what):
    self.log(what, Logger.LOG_LEVEL_INFO)

  def log_warning(self, what):
    self.log(what, Logger.LOG_LEVEL_WARNING)

  def log_error(self, what):
    self.log(what, Logger.LOG_LEVEL_ERROR)
