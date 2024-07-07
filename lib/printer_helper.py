#  Copyright 2019-2024 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
import os
import math
import pydoc
from lib._typing import List
from beartype import beartype

# 'R' to keep colors - 'X' to keep the screen - 'F' no paging if one screen
PAGER_COMMAND = 'less -R -X -F'


class FormattedString():
  """
    Class to manage difference between String that is printed and String
    that is stored.
    Usefull when String are colorized or stylished because some specific
    non-printable characters are used.
  """

  def __init__(
          self,
          str_to_be_printed: str,
          str_raw: str,
          len_to_be_printed: int):
    self.to_be_printed = str_to_be_printed
    self.raw = str_raw
    self.len_to_be_printed = len_to_be_printed

  def rstrip(self) -> "FormattedString":
    new_raw = self.raw.rstrip()
    result = FormattedString(
        self.to_be_printed.rstrip(),
        new_raw,
        len(new_raw))
    return result

  @staticmethod
  @beartype
  def build_from_string(what: str) -> "FormattedString":
    return FormattedString(what, what, len(what))

  @staticmethod
  @beartype
  def build_from_colorized_string(
          what: str,
          raw_what: str) -> "FormattedString":
    return FormattedString(what, raw_what, len(raw_what))

  @staticmethod
  def concat(*args) -> "FormattedString":
    result = FormattedString("", "", 0)
    for s in args:
      if isinstance(s, str):
        result.to_be_printed += s
        result.raw += s
        result.len_to_be_printed += len(s)
      elif isinstance(s, FormattedString):
        result.to_be_printed += s.to_be_printed
        result.raw += s.to_be_printed
        result.len_to_be_printed += s.len_to_be_printed

    return result


class ColumnsPrinter():

  def __init__(self, sbc):
    self.sbc = sbc  # space between column

  def is_printable(self, max_len_line, elts, nb_columns):
    # elts = list of FormattedString
    nb_elts = len(elts)
    nb_lines = 1 + math.floor((len(elts) - 1) / nb_columns)

    column_sizes = [0] * nb_columns
    w = 0
    for i in range(0, nb_lines):
      elt = elts[i]
      c = 0
      if elt.len_to_be_printed > column_sizes[c]:
        column_sizes[c] = elt.len_to_be_printed
      w = column_sizes[0]

      for j in range(i + nb_lines, nb_elts, nb_lines):
        elt = elts[j]
        c += 1
        if elt.len_to_be_printed > column_sizes[c]:
          column_sizes[c] = elt.len_to_be_printed
        w += self.sbc + column_sizes[c]

      for d in range(c + 1, nb_columns):
        w += self.sbc + column_sizes[d]

      if w > max_len_line:
        return False

    return True

  def column_sizes(self, elts, nb_columns):
    # elts = list of FormattedString
    nb_elts = len(elts)
    nb_lines = 1 + math.floor((len(elts) - 1) / nb_columns)
    column_sizes = [0] * nb_columns
    for i in range(0, nb_lines):
      elt = elts[i]
      w = elt.len_to_be_printed
      c = 0
      if w > column_sizes[c]:
        column_sizes[c] = w

      for j in range(i + nb_lines, nb_elts, nb_lines):
        c += 1
        elt = elts[j]
        if elt.len_to_be_printed > column_sizes[c]:
          column_sizes[c] = elt.len_to_be_printed
        w += self.sbc + column_sizes[c]

    return column_sizes

  def nb_columns(self, elts):
    # elts = list of FormattedString
    low = 1
    high = 10
    while high - low > 1:
      mid = round((low + high) / 2)
      ans = self.is_printable(os.get_terminal_size().columns, elts, mid)
      if ans:
        low = mid
      else:
        high = mid
    if self.is_printable(os.get_terminal_size().columns, elts, high):
      return high
    else:
      return low

  @beartype
  def format_with_columns(self, what: List[FormattedString]) -> str:
    # what : list of FormattedString to be printed
    if len(what) == 0:
      return ""
    nbc = self.nb_columns(what)
    cs = self.column_sizes(what, nbc)
    nb_lines = 1 + math.floor((len(what) - 1) / nbc)
    str_to_be_printed = ""
    for i in range(0, nb_lines):
      k = 0
      new_line = alignleft(what[i], cs[k])
      for j in range(i + nb_lines, len(what), nb_lines):
        k += 1
        new_line = FormattedString.concat(
            new_line,
            " " * self.sbc,
            alignleft(
                what[j],
                cs[k]))
      str_to_be_printed += new_line.to_be_printed.rstrip() + "\n"

    # remove trailing carriage return
    str_to_be_printed = str_to_be_printed[:-1]
    return str_to_be_printed

  def print_with_columns(self, what, with_pagination=False):
    str_to_be_printed = self.format_with_columns(what)
    print_with_optional_paging(str_to_be_printed, with_pagination)


@beartype
def alignright(
        printable_what: FormattedString,
        nb: int,
        fillchar=" ") -> FormattedString:
  return FormattedString.build_from_colorized_string(
      f"{(fillchar * (nb - printable_what.len_to_be_printed))}{printable_what.to_be_printed}",
      f"{(fillchar * (nb - printable_what.len_to_be_printed))}{printable_what.raw}")


@beartype
def alignleft(
        printable_what: FormattedString,
        nb: int,
        fillchar=" ") -> FormattedString:
  return FormattedString.build_from_colorized_string(
      f"{printable_what.to_be_printed}{(fillchar * (nb - printable_what.len_to_be_printed))}",
      f"{printable_what.raw}{(fillchar * (nb - printable_what.len_to_be_printed))}")


@beartype
def print_with_optional_paging(what: str,
                               with_pagination: bool = False) -> None:
  if with_pagination:
    pydoc.pipepager(what, cmd=PAGER_COMMAND)
  else:
    print(what)
