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

  def __init__(self, filename, loglevel):
    self.filename = filename
    if loglevel is None:
      self.loglevel = Logger(None, 4)
    else:
      self.loglevel = loglevel

  def log(self, what, level):
    """
        Log something according to level
    """
    if self.filename is None:
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
      tobelogged += " - " + what + "\n"
      F = open(self.filename, "a")

      F.write(tobelogged)

      F.close()
    return 1

  def log_debug(self, what):
    self.log(what, Logger.LOG_LEVEL_DEBUG)

  def log_info(self, what):
    self.log(what, Logger.LOG_LEVEL_INFO)

  def log_warning(self, what):
    self.log(what, Logger.LOG_LEVEL_WARNING)

  def log_error(self, what):
    self.log(what, Logger.LOG_LEVEL_ERROR)
