#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
import math
import os
from platform import platform
import sys
# readline introduce history management in prompt
import readline
import shlex
from abc import ABC, abstractmethod
from re import fullmatch

from beartype import beartype

from lib.graph_helper import MsGraphClient
from lib.log import Logger
from lib.oi_factory import ObjectInfoFactory


class MsObject(ABC):

  @property
  @abstractmethod
  def id():
    pass

  @property
  @abstractmethod
  def path():
    pass

  @property
  @abstractmethod
  def name():
    pass

  @abstractmethod
  def str_full_details(self):
    pass

  @property
  def __isabstractmethod__(self):
    return any(getattr(f, '__isabstractmethod__', False) for
               f in (self._fget, self._fset, self._fdel))


class MsFolderInfo(MsObject):

  @beartype
  def __init__(
          self,
          name: str,
          full_path: str,
          mgc: MsGraphClient,
          id: str = "0",
          child_count: int = None,
          size: int = None,
          parent=None):
    """
        Init folder info
        mgc   = MsGraphClient
    """
    self.__id = id
    self.__full_path = full_path
    self.__name = name
    self.__mgc = mgc
    self.children_file = []
    self.children_folder = []
    self.__dict_children_file = {}
    self.__dict_children_folder = {}
    self.next_link_children = None

    self.parent = parent
    self.child_count = child_count
    self.size = size

    self.__children_files_retrieval_status = None    # None,"partial" or "all"
    self.__children_folders_retrieval_status = None  # None, "partial" or "all"

  def get_full_path(self):
    return self.__full_path
  path = property(get_full_path)

  def _get_id(self):
    return self.__id
  id = property(_get_id)

  def _get_name(self):
    return self.__name
  name = property(_get_name)

  def retrieve_children_info(
          self,
          only_folders=False,
          recursive=False,
          depth=999):
    self.__mgc.logger.log_debug(
        f"[retrieve_children_info] {self.get_full_path()} - only_folders = {only_folders} - depth = {depth}")

    if depth > 0 and (
        only_folders and not self.folders_retrieval_has_started()
        or not self.files_retrieval_has_started() or not self.folders_retrieval_has_started()
    ):

      (ms_response, next_link) = self.__mgc.get_ms_response_for_children_folder_path(
          self.get_full_path(), only_folders)
      self.next_link_children = next_link

      for c in ms_response:
        isFolder = 'folder' in c
        if isFolder and not self.folders_retrieval_has_started():
          fi = ObjectInfoFactory.MsFolderFromMgcResponse(self.__mgc, c, self)
          self.add_folder_info(fi)
          if recursive:
            fi.retrieve_children_info(
                only_folders=only_folders,
                recursive=recursive,
                depth=depth - 1)

        elif not only_folders and not isFolder:
          fi = ObjectInfoFactory.MsFileInfoFromMgcResponse(self.__mgc, c)
          self.add_file_info(fi)
        else:
          self.__mgc.logger.log_info(
              "retrieve_children_info : UNKNOWN RESPONSE")

      self.__add_default_folder_info()
      self.__mgc.logger.log_debug(
          f"[retrieve_children_info] {self.get_full_path()} - setting retrieval status")

      if not only_folders:
        self.__children_files_retrieval_status = "partial" if self.next_link_children is not None else "all"

      self.__children_folders_retrieval_status = "partial" if self.next_link_children is not None else "all"

  def retrieve_children_info_next(
          self,
          only_folders=False,
          recursive=False,
          depth=999):
    self.__mgc.logger.log_debug(
        f"[retrieve_children_info_next] {self.get_full_path()} - only_folders = {only_folders} - depth = {depth}")

    if depth > 0 and (
        only_folders and not self.__children_folders_retrieval_status != "all"
        or self.__children_folders_retrieval_status != "all"
    ):

      (ms_response, next_link) = self.__mgc.get_ms_response_for_children_folder_path_from_link(
          self.next_link_children, only_folders)
      self.next_link_children = next_link

      for c in ms_response:
        isFolder = 'folder' in c
        if isFolder:
          fi = ObjectInfoFactory.MsFolderFromMgcResponse(self.__mgc, c, self)
          self.add_folder_info(fi)
          if recursive:
            fi.retrieve_children_info(
                only_folders=only_folders,
                recursive=recursive,
                depth=depth - 1)

        elif not only_folders and not isFolder:
          fi = ObjectInfoFactory.MsFileInfoFromMgcResponse(self.__mgc, c)
          self.add_file_info(fi)
        else:
          self.__mgc.logger.log_info(
              "retrieve_children_info : UNKNOWN RESPONSE")

      self.__mgc.logger.log_debug(
          f"[retrieve_children_info_from_link] {self.next_link_children} - setting retrieval status")

      if not only_folders:
        self.__children_files_retrieval_status = "partial" if self.next_link_children is not None else "all"

      self.__children_folders_retrieval_status = "partial" if self.next_link_children is not None else "all"

  def create_empty_subfolder(self, folder_name):
    creation_ok = self.__mgc.create_folder(self.get_full_path(), folder_name)
    if creation_ok:
      new_folder_info = MsFolderInfo(
          folder_name,
          "{0}/{1}".format(self.get_full_path(), folder_name),
          self.__mgc,
          parent=self)
      self.add_folder_info(new_folder_info)
      if self.child_count is not None:
        self.child_count += 1
      return new_folder_info
    else:
      return None

  def add_folder_info(self, folder_info):
    self.children_folder.append(folder_info)
    self.__dict_children_folder[folder_info.name] = folder_info

  def __add_default_folder_info(self):
    # add subfolder "." and "..""
    self.__dict_children_folder["."] = self
    self.__dict_children_folder[".."] = self.parent

  def add_file_info(self, file_info):
    self.children_file.append(file_info)
    self.__dict_children_file[file_info.name] = file_info

  def is_direct_child_folder(
          self,
          folder_name,
          force_children_retrieval=False):
    if force_children_retrieval and not self.folders_retrieval_has_started:
      self.retrieve_children_info(only_folders=True)
    return folder_name in self.__dict_children_folder

  def is_child_folder(self, folder_path, force_children_retrieval=False):
    return self.get_child_folder(
        folder_path, force_children_retrieval) is not None

  def is_child_file(self, file_name):
    return file_name in self.__dict_children_file

  def get_direct_child_folder(
          self,
          folder_name,
          force_children_retrieval=False):
    if force_children_retrieval and not self.folders_retrieval_has_started:
      self.retrieve_children_info(only_folders=True)
    return self.__dict_children_folder[folder_name] if folder_name in self.__dict_children_folder else None

  def get_child_folder(self, folder_path, force_children_retrieval=False):
    path_parts = folder_path.split("/")
    if path_parts[-1] == "":
      path_parts = path_parts[:-1]
    search_folder = self
    for f in path_parts:
      if search_folder.is_direct_child_folder(f, force_children_retrieval):
        search_folder = search_folder.get_direct_child_folder(f)
      else:
        return None
    return search_folder

  def get_child_file(self, file_name):
    return self.__dict_children_file[file_name] if file_name in self.__dict_children_file else None

  def files_retrieval_has_started(self):
    return self.__children_files_retrieval_status == "all" or self.__children_files_retrieval_status == "partial"

  def folders_retrieval_has_started(self):
    return self.__children_folders_retrieval_status == "all" or self.__children_folders_retrieval_status == "partial"

  def files_retrieval_is_completed(self):
    return self.__children_files_retrieval_status == "all"

  def folders_retrieval_is_completed(self):
    return self.__children_folders_retrieval_status == "all"

  def __str__(self):
    status_subfolders = "<subfolders ok>" if self.folders_retrieval_has_started() else ""
    status_subfiles = "<subfiles ok>" if self.files_retrieval_has_started() else ""

    fname = f"{self.name}/" if len(self.name) < 25 else f"{self.name[:20]}.../"
    result = f"{self.size:>20,}  {fname:<25}  {self.child_count:>6}  {status_subfolders}{status_subfiles}"
    return result

  def str_full_details(self):
    result = ("Folder {0}\n"
              "name = {1}").format(
        self.get_full_path()[1:],
        self.name
    )

    return result

  def __repr__(self):
    return f"Folder({self.name})"


class MsFileInfo(MsObject):
  def __init__(
          self,
          name,
          parent_path,
          mgc,
          file_id,
          size,
          qxh,
          s1h,
          cdt,
          lmdt):
    # qxh = quickxorhash
    self.mgc = mgc
    self.__name = name
    self.__parent_path = parent_path
    self.__id = file_id
    self.size = size
    self.sha1hash = s1h
    self.qxh = qxh
    self.creation_datetime = cdt
    self.last_modified_datetime = lmdt

  def _get_path(self):
    return "/{0}/{1}".format(self.__parent_path, self.__name)
  path = property(_get_path)

  def _get_id(self):
    return self.__id
  id = property(_get_id)

  def _get_name(self):
    return self.__name
  name = property(_get_name)

  def __str__(self):
    fname = f"{self.name}" if len(self.name) < 45 else f"{self.name[:40]}..."
    fmdt = self.last_modified_datetime.strftime("%Y-%m-%d %H:%M:%S")
    result = f"{self.size:>20,}  {fname:<45}  {fmdt}  "
    return result

  def str_full_details(self):
    result = (
        "File - '{0}'\n"
        "  name                  = {1}\n"
        "  full_path             = {2}\n"
        "  id                    = {3:>20}\n"
        "  size                  = {4:,}\n"
        "  quickXorHash          = {5}\n"
        "  sha1Hash              = {6}\n"
        "  creationDateTime      = {7}\n"
        "  lastModifiedDateTime  = {8}"
    ).format(
        self.name,
        self.name,
        self.path,
        self.__id,
        self.size,
        self.qxh,
        self.sha1hash,
        self.creation_datetime,
        self.last_modified_datetime)

    return result

  def __repr__(self):
    return f"File({self.name})"


class StrPathUtil:
  __TO_BE_ESCAPED = ('\\', ' ', '\'') if sys.platform != "win32" else (
      ' ')  # \\ MUST be the first one

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
  def test():
    ip = input("> ")
    print(f"result = {StrPathUtil.escape_str(ip)}")


class Completer:

  #
  # Everything is replaced in the readline buffer to managed folder name with space
  #
  # To avoid misunderstanding, only the folder name is displayed in the
  # match list

  def __init__(self, odshell, lg=None):
    self.shell = odshell
    self.values = []
    self.start_line = ""
    self.new_start_line = ""
    self.columns_printer = ColumnsPrinter(2)
    self.lg = lg

  def __log_debug(self, what):
    if self.lg is not None:
      self.lg.log_debug(f"[complete]{what}")

  def display_matches(self, what, matches, longest_match_length):
    try:
      self.__log_debug(f"[display matches]dm('{what}',{matches})")
      print("")

      # remove start_line from matches
      to_be_printed = list(
          map(lambda x: x[len(self.new_start_line):], matches))
      self.columns_printer.print_with_columns(to_be_printed)
      print(
          f"{self.shell.get_prompt()}{readline.get_line_buffer()}",
          end="",
          flush=True)

    except Exception as e:
      print(f"Exception = {e}")

  def __get_cmd_parts_with_quotation_guess(self, input):
    try:
      # WARNING: does not work with win32 if a backslash is included in input
      return shlex.split(input)

    except ValueError as e:
      try:
        return shlex.split(input + "'")

      except ValueError as e:
        return shlex.split(input + '"')

  @beartype
  def complete(self, text: str, state: int):

    self.__log_debug(f"complete('{text}',{state})")
    line = readline.get_line_buffer()
    try:

      parts_cmd = self.__get_cmd_parts_with_quotation_guess(line)

      if len(parts_cmd) > 0 and parts_cmd[0] == "cd":

        if state == 0:
          # Get last part of full_path and extract start_text of folder name
          if len(parts_cmd) > 1:
            folder_names_str = parts_cmd[1]
            folder_names = StrPathUtil.split_path(folder_names_str)
            if folder_names_str[-1] == os.sep:
              start_text = ""
            else:
              start_text = folder_names[-1]
              # remove the last folder name which is the start text
              folder_names = folder_names[:-1]
              folder_names_str = os.sep.join(folder_names)
              if len(folder_names) > 0:  # was 1 before removing
                folder_names_str = folder_names_str + os.sep
          else:
            folder_names_str = ""
            folder_names = []
            start_text = ""

          # Extract start of text to be escaped if necessary
          self.new_start_line = "cd " + \
              StrPathUtil.escape_str(folder_names_str)

          # Get folder info of last folders in given path
          search_folder = self.shell.current_fi
          for f in folder_names:
            if search_folder.is_child_folder(f):
              search_folder = search_folder.get_direct_child_folder(f, True)
            else:
              break

          # Compute list of substitute string
          #   1. Compute folder names
          #   2. Keep folders whose name starts with start_text
          #   2. Add escaped folder name
          folders = map(lambda x: x.name, search_folder.children_folder)
          folders = filter(lambda x: x.startswith(start_text), folders)
          folders = map(lambda x: StrPathUtil.escape_str(x), folders)
          folders = map(lambda x: f"{self.new_start_line}{x}{os.sep}", folders)
          self.values = list(folders)
          self.__log_debug(f"values = {','.join(self.values)}")

        if state < len(self.values):
          self.__log_debug(f"  --> return {self.values[state]}")
          return self.values[state]
        else:
          return None

      return None
    except Exception as e:
      print(f"[complete]Exception = {e}")


class OneDriveShell:

  def __init__(self, mgc):
    self.mgc = mgc
    self.current_fi = MsFolderInfo("", "", self.mgc)
    self.root_folder = self.current_fi
    self.only_folders = False
    self.ls_formatter = LsFormatter(MsFileFormatter(45), MsFolderFormatter(45))

  def change_max_column_size(self, nb):
    self.ls_formatter = LsFormatter(MsFileFormatter(nb), MsFolderFormatter(nb))

  def change_current_folder_to_parent(self):
    if self.current_fi.parent is not None:
      self.current_fi = self.current_fi.parent
    else:
      print("The current folder has no parent")

  def get_prompt(self):
    result = self.current_fi.name
    if self.current_fi.next_link_children is not None:
      result += "..."
    result += "> "
    return result

  def launch(self):

    cp = Completer(self, lg=Logger("./log_complete.txt", 4))
    #cp = Completer(self)

    readline.parse_and_bind('tab: complete')
    readline.set_completer(cp.complete)
    if sys.platform != "win32":
      readline.set_completion_display_matches_hook(cp.display_matches)
    # All line content will be managed by complemtion
    readline.set_completer_delims("")

    self.current_fi.retrieve_children_info(
        only_folders=self.only_folders, recursive=False)

    while True:

      my_input = input(f"{self.get_prompt()}")
      # Trim my_input and remove double spaces
      my_input = " ".join(my_input.split())
      my_input = my_input.replace(" = ", "=")
      parts_cmd = shlex.split(my_input)
      if len(parts_cmd) > 0:
        cmd = parts_cmd[0]
      else:
        cmd = ""

      if cmd == "quit":
        break

      if cmd == "pwd":
        print(self.current_fi.path)

      elif cmd == "ll":
        if self.current_fi.parent is not None:
          print("  0 - <parent>")
        self.ls_formatter.print_folder_children(
            self.current_fi, start_number=1, only_folders=self.only_folders)

      elif cmd == "ls":
        self.ls_formatter.print_folder_children_lite(
            self.current_fi, only_folders=self.only_folders)

      elif cmd == "lls":
        self.ls_formatter.print_folder_children_lite_next(
            self.current_fi, only_folders=self.only_folders)

      elif cmd == "cd":
        if len(parts_cmd) == 2:
          self.change_to_path(parts_cmd[1])

      elif cmd == "cd..":
        self.change_current_folder_to_parent()

      elif cmd.isdigit() and int(cmd) <= len(self.current_fi.children_folder):

        int_input = int(cmd)
        if int_input == 0:
          self.change_current_folder_to_parent()
        else:
          self.current_fi = self.current_fi.children_folder[int(my_input) - 1]

      elif my_input == "set onlyfolders" or my_input == "set of":
        self.only_folders = True

      elif my_input == "set noonlyfolders" or my_input == "set noof":
        self.only_folders = False

      elif my_input[:7] == "set cs=" or my_input[:15] == "set columnsize=":
        str_cs = my_input[7:] if my_input[:7] == "set cs=" else my_input[15:]

        if not str_cs.isdigit():
          print("<value> of column size must be a digit")
        else:
          int_cs = int(str_cs)
          if (int_cs < 5) or (int_cs > 300):
            print("<value> must be a number between 5 and 300")
          else:
            self.change_max_column_size(int_cs)

      elif cmd == "help" or cmd == "h":
        print("Onedrive Browser Help")
        print("")
        print("COMMAND")
        print("   set onlyfolders")
        print("   set of                : Retrieve info only about folders")
        print("   set noonlyfolders")
        print("   set noof              : Retrieve info about folders and files")
        print("   set columnsize")
        print("   set cs                : Set column size for name")
        print("   ls                    : List current folder by columns")
        print("   lls                   : Continue listing folder in case of large folder")
        print("   cd <folder path>      : Change to folder path")
        print("   ll                    : List Folder with details")
        print("   pwd                   : Print full path of current folder")
        print("   <number>              : Dig into given folder")
        print("   q")
        print("   quit                  : Quit Browser")

      elif cmd == "":
        pass

      else:
        print("unknown command")

  def change_to_path(self, folder_path):

    # Compute relative path from root_folder
    if folder_path[0] != os.sep:
      full_path = os.path.normpath(
          self.current_fi.get_full_path() +
          os.sep +
          folder_path)[
          1:]
    else:
      full_path = os.path.normpath(folder_path[1:])

    if self.root_folder.is_child_folder(full_path):
      self.current_fi = self.root_folder.get_child_folder(full_path)


class InfoFormatter(ABC):

  @abstractmethod
  def format(self, what):
    return "default"

  @abstractmethod
  def format_lite(self, what):
    return "default"

  @staticmethod
  def alignright(what, nb, fillchar=" "):
    return f"{(fillchar * (nb - len(what)))}{what}"

  @staticmethod
  def alignleft(what, nb, fillchar=" "):
    return f"{what}{(fillchar * (nb - len(what)))}"


class MsFolderFormatter(InfoFormatter):

  def __init__(self, max_name_size=25):
    self.max_name_size = max_name_size

  @beartype
  def format(self, what: MsFolderInfo):
    status_subfolders = "<subfolders ok>" if what.folders_retrieval_has_started() else ""
    status_subfiles = "<subfiles ok>" if what.files_retrieval_has_started() else ""

    fname = f"{what.name}/" if len(
        what.name) < self.max_name_size else f"{what.name[:self.max_name_size - 5]}.../"
    result = (
        f"{what.size:>20,}  {InfoFormatter.alignleft(fname,self.max_name_size)}"
        f"  {what.child_count:>6}  {status_subfolders}{status_subfiles}")
    return result

  @beartype
  def format_lite(self, what: MsFolderInfo):
    return f"{what.name}/"


class MsFileFormatter(InfoFormatter):
  def __init__(self, max_name_size=25):
    self.max_name_size = max_name_size

  @beartype
  def format(self, what: MsFileInfo):
    fname = f"{what.name}" if len(
        what.name) < self.max_name_size else f"{what.name[:self.max_name_size - 5]}..."
    fmdt = what.last_modified_datetime.strftime("%Y-%m-%d %H:%M:%S")
    result = f"{what.size:>20,}  {InfoFormatter.alignleft(fname,self.max_name_size)}  {fmdt}  "
    return result

  @beartype
  def format_lite(self, what: MsFileInfo):
    return what.name


class LsFormatter():

  @beartype
  def __init__(self, file_formatter: MsFileFormatter,
               folder_formatter: MsFolderFormatter):
    self.file_formatter = file_formatter
    self.folder_formatter = folder_formatter
    self.column_printer = ColumnsPrinter(2)

  @beartype
  def print_folder_children(
          self,
          fi: MsFolderInfo,
          start_number: int = 0,
          recursive: bool = False,
          only_folders: bool = True,
          depth: int = 999):
    if ((not fi.folders_retrieval_has_started() and only_folders)
            or (not fi.files_retrieval_has_started() and not only_folders)):
      fi.retrieve_children_info(
          only_folders=only_folders,
          recursive=recursive,
          depth=depth)

    i = start_number
    for c in fi.children_folder:
      print(f"{i:>3} - {self.folder_formatter.format(c)}")
      i = i + 1
    if not only_folders:
      for c in fi.children_file:
        print(f"{i:>3} - {self.file_formatter.format(c)}")
        i = i + 1

    if recursive and depth > 0:
      for c in fi.children_folder:
        nb_children = c.print_children(
            start_number=i, recursive=False, depth=depth - 1)

        i += nb_children

    return i - start_number

  @beartype
  def print_folder_children_lite(
          self,
          fi: MsFolderInfo,
          only_folders: bool = True):
    if ((not fi.folders_retrieval_has_started() and only_folders)
            or (not fi.files_retrieval_has_started() and not only_folders)):
      fi.retrieve_children_info(only_folders=only_folders)

    folder_names = map(
        lambda x: self.folder_formatter.format_lite(x),
        fi.children_folder)
    file_names = map(
        lambda x: self.file_formatter.format_lite(x),
        fi.children_file)
    all_names = list(folder_names) + list(file_names)
    self.column_printer.print_with_columns(all_names)

  @beartype
  def print_folder_children_lite_next(
          self, fi: MsFolderInfo, only_folders: bool = True):
    if ((not fi.folders_retrieval_is_completed() and only_folders)
            or (not fi.files_retrieval_is_completed() and not only_folders)):
      fi.retrieve_children_info_next(only_folders=only_folders)

    self.print_folder_children_lite(fi, only_folders)


class ColumnsPrinter():

  def __init__(self, sbc):
    self.sbc = sbc  # space between column

  def is_printable(self, max_len_line, elts, nb_columns):
    nb_elts = len(elts)
    nb_lines = 1 + math.floor((len(elts) - 1) / nb_columns)

    column_sizes = [0] * nb_columns
    w = 0
    for i in range(0, nb_lines):
      elt = elts[i]
      c = 0
      if len(elt) > column_sizes[c]:
        column_sizes[c] = len(elt)
      w = column_sizes[0]

      for j in range(i + nb_lines, nb_elts, nb_lines):
        elt = elts[j]
        c += 1
        if len(elt) > column_sizes[c]:
          column_sizes[c] = len(elt)
        w += self.sbc + column_sizes[c]

      for d in range(c + 1, nb_columns):
        w += self.sbc + column_sizes[d]

      if w > max_len_line:
        return False

    return True

  def column_sizes(self, elts, nb_columns):
    nb_elts = len(elts)
    nb_lines = 1 + math.floor((len(elts) - 1) / nb_columns)
    column_sizes = [0] * nb_columns
    for i in range(0, nb_lines):
      elt = elts[i]
      w = len(elt)
      c = 0
      if len(elt) > column_sizes[c]:
        column_sizes[c] = len(elt)

      for j in range(i + nb_lines, nb_elts, nb_lines):
        c += 1
        elt = elts[j]
        if len(elt) > column_sizes[c]:
          column_sizes[c] = len(elt)
        w += self.sbc + column_sizes[c]

    return column_sizes

  def nb_columns(self, elts):
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

  def print_with_columns(self, what):
    # what : string list to be printed
    nbc = self.nb_columns(what)
    cs = self.column_sizes(what, nbc)
    nb_lines = 1 + math.floor((len(what) - 1) / nbc)
    for i in range(0, nb_lines):
      k = 0
      new_line = InfoFormatter.alignleft(what[i], cs[k])
      for j in range(i + nb_lines, len(what), nb_lines):
        k += 1
        new_line += " " * self.sbc + InfoFormatter.alignleft(what[j], cs[k])
      print(new_line)
