#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
from re import fullmatch
from abc import ABC, abstractmethod
from beartype import beartype
from lib.oi_factory import ObjectInfoFactory
from lib.graph_helper import MsGraphClient


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
    self.parent = parent
    self.child_count = child_count
    self.size = size

    self.__children_files_retrieval_status = None
    self.__children_folders_retrieval_status = None

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
        only_folders and not self.folders_have_been_retrieved()
        or not self.files_have_been_retrieved() or not self.folders_have_been_retrieved()
    ):

      ms_response = self.__mgc.get_ms_response_for_children_folder_path(
          self.get_full_path(), only_folders)

      self.__children_folders_retrieval_status = "in_progress"

      if not only_folders:
        self.__children_files_retrieval_status = "in_progress"

      for c in ms_response:
        isFolder = 'folder' in c
        if isFolder and not self.folders_have_been_retrieved():
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
        self.__children_files_retrieval_status = "all"

      self.__children_folders_retrieval_status = "all"

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

  def files_have_been_retrieved(self):
    return self.__children_files_retrieval_status == "all"

  def folders_have_been_retrieved(self):
    return self.__children_folders_retrieval_status == "all"

  def __str__(self):
    status_subfolders = "<subfolders ok>" if self.folders_have_been_retrieved() else ""
    status_subfiles = "<subfiles ok>" if self.files_have_been_retrieved() else ""

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
    self.file_formatter = MsFileFormatter(45)
    self.folder_formatter = MsFolderFormatter(45)

  def change_max_column_size(self, nb):
    self.file_formatter = MsFileFormatter(nb)
    self.folder_formatter = MsFolderFormatter(nb)

  def launch(self):
     # current_folder_info = mgc.get_folder_info("")
    current_folder_info = MsFolderInfo("", "", self.mgc)

    while True:

      prompt = current_folder_info.name

      my_input = input(f"{prompt}> ")
      # Trim my_input and remove double spaces
      my_input = " ".join(my_input.split())
      my_input = my_input.replace(" = ", "=")

      if my_input == "quit":
        break

      if my_input == "ls":
        if current_folder_info.parent is not None:
          print("  0 - <parent>")
        self.print_folder_children(
            current_folder_info,
            start_number=1,
            only_folders=self.only_folders)

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
        print("   ls                    : List current folder")
        print("   <number>              : Dig into given folder")
        print("   q")
        print("   quit                  : Quit Browser")

      else:
        print("unknown command")

      print("")

  def print_folder_children(
          self,
          fi,
          start_number=0,
          recursive=False,
          only_folders=True,
          depth=999):
    if ((not fi.folders_have_been_retrieved() and only_folders)
            or (not fi.files_have_been_retrieved() and not only_folders)):
      self.mgc.logger.log_debug(
          f"[print_children] folder_path = {fi.get_full_path()} - folders have not been retrieved")
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


class InfoFormatter(ABC):

  @abstractmethod
  def format(self, what):
    return "default"

  @staticmethod
  def alignright(what, nb, fillchar=" "):
    return f"{(fillchar * (nb - len(what)))}{what}"


class MsFolderFormatter(InfoFormatter):

  def __init__(self, max_name_size=25):
    self.max_name_size = max_name_size

  @beartype
  def format(self, what: MsFolderInfo):
    status_subfolders = "<subfolders ok>" if what.folders_have_been_retrieved() else ""
    status_subfiles = "<subfiles ok>" if what.files_have_been_retrieved() else ""

    fname = f"{what.name}/" if len(
        what.name) < self.max_name_size else f"{what.name[:self.max_name_size - 5]}.../"
    result = (
        f"{what.size:>20,}  {InfoFormatter.alignright(fname,self.max_name_size)}"
        f"  {what.child_count:>6}  {status_subfolders}{status_subfiles}")
    return result


class MsFileFormatter(InfoFormatter):
  def __init__(self, max_name_size=25):
    self.max_name_size = max_name_size

  @beartype
  def format(self, what: MsFileInfo):
    fname = f"{what.name}" if len(
        what.name) < self.max_name_size else f"{what.name[:self.max_name_size - 5]}..."
    fmdt = what.last_modified_datetime.strftime("%Y-%m-%d %H:%M:%S")
    result = f"{what.size:>20,}  {InfoFormatter.alignright(fname,self.max_name_size)}  {fmdt}  "
    return result
