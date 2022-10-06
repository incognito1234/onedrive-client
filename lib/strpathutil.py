#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
import os
import sys


class StrPathUtil:
  __TO_BE_ESCAPED = (
      '\\', ' ', '\'', '(', ')') if sys.platform != "win32" else (
      ' ', '(', ')')  # \\ MUST be the first one

  @staticmethod
  def escape_str(what):
    result = what
    for c in StrPathUtil.__TO_BE_ESCAPED:
      result = result.replace(c, f"\\{c}")

    return result

  @staticmethod
  def split_path(full_path):
    fp = full_path
    # fp = shlex.split(full_path)[0]  # remove quote and escape sequence
    fp = os.path.normpath(fp)
    result = []
    while (fp != os.sep) and (fp != ""):
      parts = os.path.split(fp)
      fp = parts[0]
      result.append(parts[1])
    if fp != "":         # Append root path if available
      result.append("")
    result.reverse()
    return result

  @staticmethod
  def remove_first_char_if_necessary(what, first_char):
    """
       Remove first char at first position of what if present
    """
    if len(what) > 0 and what[0] == first_char:
      return what[1:]
    return what

  @staticmethod
  def add_first_char_if_necessary(what, first_char):
    """
       Add first char at first position of what if not present
    """
    if (len(what) > 0 and what[0] != first_char) or (what == ""):
      return f"{first_char}{what}"
    return what

  @staticmethod
  def test():
    ip = input("> ")
    print(f"result = {StrPathUtil.escape_str(ip)}")
