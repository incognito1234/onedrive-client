#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
from re import fullmatch
from abc import ABC, abstractmethod
import math
from beartype import beartype
from lib.oi_factory import ObjectInfoFactory
from lib.graph_helper import MsGraphClient
import os


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
          self.__mgc.Logger.log_info(
              "retrieve_children_info : UNKNOWN RESPONSE")

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
          self.__mgc.Logger.log_info(
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

  def add_file_info(self, file_info):
    self.children_file.append(file_info)
    self.__dict_children_file[file_info.name] = file_info

  def is_child_folder(self, folder_name):
    return folder_name in self.__dict_children_folder

  def is_child_file(self, file_name):
    return file_name in self.__dict_children_file

  def get_child_folder(self, folder_name):
    return self.__dict_children_folder[folder_name] if folder_name in self.__dict_children_folder else None

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


class OneDriveShell:

  def __init__(self, mgc):
    self.mgc = mgc
    self.only_folders = False
    self.ls_formatter = LsFormatter(MsFileFormatter(45), MsFolderFormatter(45))

  def change_max_column_size(self, nb):
    self.ls_formatter = LsFormatter(MsFileFormatter(nb), MsFolderFormatter(nb))

  def launch(self):
     # current_folder_info = mgc.get_folder_info("")
    current_folder_info = MsFolderInfo("", "", self.mgc)
    current_folder_info.retrieve_children_info(
        only_folders=self.only_folders, recursive=False)

    while True:

      prompt = current_folder_info.name
      if current_folder_info.next_link_children is not None:
        prompt += "..."

      my_input = input(f"{prompt}> ")
      # Trim my_input and remove double spaces
      my_input = " ".join(my_input.split())
      my_input = my_input.replace(" = ", "=")

      if my_input == "quit":
        break

      if my_input == "ll":
        if current_folder_info.parent is not None:
          print("  0 - <parent>")
        self.ls_formatter.print_folder_children(
            current_folder_info, start_number=1, only_folders=self.only_folders)

      elif my_input == "ls":
        self.ls_formatter.print_folder_children_lite(
            current_folder_info, only_folders=self.only_folders)

      elif my_input == "lls":
        self.ls_formatter.print_folder_children_lite_next(
            current_folder_info, only_folders=self.only_folders)

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

      elif my_input.isdigit() and int(my_input) <= len(current_folder_info.children_folder):

        int_input = int(my_input)
        if int_input == 0 and current_folder_info.parent is not None:
          current_folder_info = current_folder_info.parent
        elif int_input == 0 and current_folder_info.parent is None:
          print("The current folder has no parent")
        else:
          current_folder_info = current_folder_info.children_folder[int(
              my_input) - 1]

      elif my_input == "help" or my_input == "h":
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
        print("   ll                    : List Folder with details")
        print("   <number>              : Dig into given folder")
        print("   q")
        print("   quit                  : Quit Browser")

      elif my_input == "":
        pass

      else:
        print("unknown command")


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
    self.sbc = 2  # Space between columns

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

  def is_printable(self, max_len_line, elts, nb_columns):
    nb_elts = len(elts)
    nb_lines = 1 + math.floor((len(elts) - 1) / nb_columns)

    column_sizes = [0] * nb_columns
    w = 0
    for i in range(0, nb_lines):
      elt = elts[i]
      w = len(elt)
      c = 0
      if len(elt) > column_sizes[c]:
        column_sizes[c] = len(elt)
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
    nbc = self.nb_columns(all_names)
    cs = self.column_sizes(all_names, nbc)
    nb_lines = 1 + math.floor((len(all_names) - 1) / nbc)
    for i in range(0, nb_lines):
      k = 0
      new_line = InfoFormatter.alignleft(all_names[i], cs[k])
      for j in range(i + nb_lines, len(all_names), nb_lines):
        k += 1
        new_line += " " * self.sbc + \
            InfoFormatter.alignleft(all_names[j], cs[k])
      print(new_line)

  @beartype
  def print_folder_children_lite_next(
          self, fi: MsFolderInfo, only_folders: bool = True):
    if ((not fi.folders_retrieval_is_completed() and only_folders)
            or (not fi.files_retrieval_is_completed() and not only_folders)):
      fi.retrieve_children_info_next(only_folders=only_folders)

    self.print_folder_children_lite(fi, only_folders)
