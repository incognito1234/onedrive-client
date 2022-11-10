#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
import logging
import math
import os
import sys
from abc import ABC, abstractmethod
from beartype import beartype
from lib._typing import Optional, Tuple
from lib.graph_helper import MsGraphClient
from lib.datetime_helper import str_from_ms_datetime
from lib.strpathutil import StrPathUtil

lg = logging.getLogger('odc.msobject')


class MsObject(ABC):

  @beartype
  def __init__(
          self,
          parent: Optional["MsFolderInfo"],
          name: str,
          parent_path: str,
          ms_id: str,
          size: int,
          is_root: bool = False):
    # Parent stat must not been updated if parent has just been initiated through mgc_response:
    #   - mgc_response contains child count, size but not all children
    self.ms_id = ms_id  # id is a keyword in python
    self.__size = size
    self.parent = parent
    self.__name = name
    self.__parent_path = parent_path
    self.__is_root = is_root  # only used to compute path

  @property
  def path(self):
    return "" if self.__is_root else f"{self.__parent_path}/{self.__name}"

  @property
  def parent_path(self):
    return self.__parent_path

  @property
  def name(self):
    return self.__name

  @property
  def size(self):
    return self.__size

  @abstractmethod
  def str_full_details(self):
    pass

  @property
  def __isabstractmethod__(self):
    return any(getattr(f, '__isabstractmethod__', False) for
               f in (self._fget, self._fset, self._fdel))

  def update_parent_before_removal(self):
    if self.parent is None:
      return

    self.parent.child_count -= 1

    current_parent = self.parent
    while current_parent is not None:
      current_parent.__size -= self.size
      current_parent = current_parent.parent

    self.parent._remove_info_for_child(self)

  @beartype
  def update_parent_after_arrival(self, new_parent: Optional["MsFolderInfo"]):
    if new_parent is None:
      return
    new_parent.child_count += 1
    current_parent = new_parent
    while current_parent is not None:
      current_parent.__size += self.__size
      current_parent = current_parent.parent
    new_parent._add_object_info(self)

  @beartype
  def move_object(self, new_parent: "MsFolderInfo"):
    self.update_parent_before_removal()
    self.parent = new_parent
    self.__parent_path = new_parent.path
    self.update_parent_after_arrival(new_parent)

  @beartype
  def rename(self, new_name: str):
    self.update_parent_before_removal()
    self.__name = new_name
    self.update_parent_after_arrival(self.parent)

  @staticmethod
  def get_lastfolderinfo_path(
          root_fi, input, current_fi=None) -> Tuple[Optional["MsFolderInfo"], Optional[str]]:
    """
      Return a tuple (<last_folder_info_path>, <remaining_text>)
    """
    my_input = input

    # Manage empty path
    if my_input == "":
      if current_fi is None:
        return (None, None)
      else:
        return (current_fi, "")

     # Manage relative path without current_fi
    if my_input[0] != "/" and current_fi is None:
      return (None, None)

    end_with_dot_or_doubledot = os.path.split(input)[1] in (".", "..")
    if end_with_dot_or_doubledot:  # Manage path ending with a dot or a double dot
      my_input = os.path.normpath(f"{my_input}a")
    else:
      my_input = os.path.normpath(f"{my_input}")

    # Build full path and normalize it (removing .. and .)
    if my_input[0] != "/":
      my_input = f"{current_fi.path}/{my_input}"

    # Search folder and extract start_text
    folder_names = StrPathUtil.split_path(my_input)
    folder_names = folder_names[1:]  # Remove first item which is ""
    if input[-1] == "/":  # Last part is a folder
      start_text = ""
    else:

      if end_with_dot_or_doubledot:  # Manage path ending with a dot or a double dot
        start_text = os.path.split(input)[1]
        # remove the last folder name which is ".a" or "..a"
        folder_names = folder_names[:-1]
      else:
        start_text = folder_names[-1]
        # remove the last folder name which is the start text
        folder_names = folder_names[:-1]

    search_folder = root_fi
    found = True
    for f in folder_names:
      if search_folder.is_direct_child_folder(f, True):
        search_folder = search_folder.get_direct_child_folder(f, True)
      else:
        found = False
        break

    if found:
      return (search_folder, start_text)
    else:
      return (None, None)


class MsFolderInfo(MsObject):

  @beartype
  def __init__(
          self,
          name: str,
          parent_path: str,
          mgc: MsGraphClient,
          id: str,
          size: int,
          child_count: int = None,
          parent=None,
          lmdt=None,
          cdt=None,
          is_root: bool = False):
    """
        Init folder info
        mgc   = MsGraphClient
    """
    super().__init__(parent, name, parent_path, id, size, is_root)
    self.__mgc = mgc
    self.children_file = []
    self.children_folder = []
    self.__dict_children_file = {}
    self.__dict_children_folder = {}
    self.next_link_children = None

    self.child_count = child_count

    self.__children_files_retrieval_status = None    # None,"partial" or "all"
    self.__children_folders_retrieval_status = None  # None, "partial" or "all"

    self.last_modified_datetime = lmdt
    self.creation_datetime = cdt

  @beartype
  def _remove_info_for_child(self, child: MsObject):
    if isinstance(child, MsFolderInfo):
      self.children_folder.remove(child)
      self.__dict_children_folder.pop(child.name)
    else:  # isinstance(child, MsFileInfo)
      self.children_file.remove(child)
      self.__dict_children_file.pop(child.name)

  def retrieve_children_info(
          self,
          only_folders=False,
          recursive=False,
          depth=999):
    lg.debug(
        f"[retrieve_children_info] {self.path} - only_folders = {only_folders} - depth = {depth}")

    if depth > 0 and (
        only_folders and not self.folders_retrieval_has_started()
        or not self.files_retrieval_has_started() or not self.folders_retrieval_has_started()
    ):

      (ms_response, next_link) = self.__mgc.get_ms_response_for_children_folder_path(
          self.path, only_folders)
      self.next_link_children = next_link

      for c in ms_response:
        isFolder = 'folder' in c
        if isFolder and not self.folders_retrieval_has_started():
          fi = ObjectInfoFactory.MsFolderFromMgcResponse(self.__mgc, c, self)
          self.__add_folder_info_if_necessary(fi)
          if recursive:
            fi.retrieve_children_info(
                only_folders=only_folders,
                recursive=recursive,
                depth=depth - 1)

        elif not only_folders and not isFolder:
          fi = ObjectInfoFactory.MsFileInfoFromMgcResponse(self.__mgc, c, self)
          self.__add_file_info_if_necessary(fi)
        # else:   - isFolder and folder already retrieved

      self.__add_default_folder_info()
      lg.debug(
          f"[retrieve_children_info] {self.path} - setting retrieval status")

      if not only_folders:
        self.__children_files_retrieval_status = "partial" if self.next_link_children is not None else "all"

      self.__children_folders_retrieval_status = "partial" if self.next_link_children is not None else "all"

  def retrieve_children_info_next(
          self,
          only_folders=False,
          recursive=False,
          depth=999):
    lg.debug(
        f"[retrieve_children_info_next] {self.path} - only_folders = {only_folders} - depth = {depth}")

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
          self.__add_folder_info_if_necessary(fi)
          if recursive:
            fi.retrieve_children_info(
                only_folders=only_folders,
                recursive=recursive,
                depth=depth - 1)

        elif not only_folders and not isFolder:
          fi = ObjectInfoFactory.MsFileInfoFromMgcResponse(self.__mgc, c)
          self.__add_file_info_if_necessary(fi)
        else:
          lg.info("retrieve_children_info : UNKNOWN RESPONSE")

      lg.debug(
          f"[retrieve_children_info_from_link] {self.next_link_children} - setting retrieval status")

      if not only_folders:
        self.__children_files_retrieval_status = "partial" if self.next_link_children is not None else "all"

      self.__children_folders_retrieval_status = "partial" if self.next_link_children is not None else "all"

  def create_empty_subfolder(self, folder_name):
    folder_json = self.__mgc.create_folder(self.path, folder_name)
    if folder_json:
      new_folder_info = MsFolderInfo(
          folder_name,
          f"{self.path}",
          self.__mgc,
          id=folder_json["id"],
          size=0,
          parent=self)
      self.__add_folder_info_if_necessary(new_folder_info)
      if self.child_count is not None:
        self.child_count += 1
      return new_folder_info
    else:
      return None

  def __add_folder_info_if_necessary(self, folder_info):
    if folder_info.name not in self.__dict_children_folder:
      self.children_folder.append(folder_info)
      self.__dict_children_folder[folder_info.name] = folder_info

  def __add_default_folder_info(self):
    # add subfolder "." and "..""
    self.__dict_children_folder["."] = self
    self.__dict_children_folder[".."] = self.parent

  def __add_file_info_if_necessary(self, file_info):
    if file_info.name not in self.__dict_children_file:
      self.children_file.append(file_info)
      self.__dict_children_file[file_info.name] = file_info

  def _add_object_info(self, object_info: MsObject):
    if isinstance(object_info, MsFolderInfo):
      self.__add_folder_info_if_necessary(object_info)
    else:  # isinstance(object_info, MsFileInfo)
      self.__add_file_info_if_necessary(object_info)

  def get_direct_child_folder(
          self,
          folder_name,
          force_children_retrieval=False):
    if force_children_retrieval and not self.folders_retrieval_has_started():
      self.retrieve_children_info(only_folders=True)
    return self.__dict_children_folder[folder_name] if folder_name in self.__dict_children_folder else None

  def get_child_folder(
          self,
          relative_folder_path,
          force_children_retrieval=False):
    path_parts = relative_folder_path.split(os.sep)
    if path_parts[-1] == "":      # folder_path ends with a "/"
      path_parts = path_parts[:-1]
    search_folder = self
    for f in path_parts:
      if search_folder.is_direct_child_folder(f, force_children_retrieval):
        search_folder = search_folder.get_direct_child_folder(
            f, force_children_retrieval)
      else:
        return None
    return search_folder

  def get_direct_child_file(self, file_name, force_children_retrieval=False):
    if force_children_retrieval and not self.folders_retrieval_has_started():
      self.retrieve_children_info(only_folders=False)
    return self.__dict_children_file[file_name] if file_name in self.__dict_children_file else None

  def get_child_file(
          self,
          relative_file_path,
          force_children_retrieval=False) -> Optional["MsFileInfo"]:
    path_parts = relative_file_path.split(os.sep)
    search_folder = self
    i = 0
    while i < (len(path_parts) - 1):
      f = path_parts[i]
      if search_folder.is_direct_child_folder(f, force_children_retrieval):
        search_folder = search_folder.get_direct_child_folder(
            f, force_children_retrieval)
      else:
        return None
      i += 1
    if search_folder.is_direct_child_file(
            path_parts[-1], force_children_retrieval):
      return search_folder.get_direct_child_file(
          path_parts[-1], force_children_retrieval)

  def is_direct_child_folder(
          self,
          folder_name,
          force_children_retrieval=False):
    if force_children_retrieval and not self.folders_retrieval_has_started():
      self.retrieve_children_info(only_folders=True)
    return folder_name in self.__dict_children_folder

  def relative_path_is_a_folder(
          self,
          relative_folder_path,
          force_children_retrieval=False):
    return self.get_child_folder(
        relative_folder_path,
        force_children_retrieval) is not None

  def is_direct_child_file(self, file_name, force_children_retrieval=False):
    if force_children_retrieval and not self.folders_retrieval_has_started():
      self.retrieve_children_info(only_folders=False)
    return file_name in self.__dict_children_file

  def relative_path_is_a_file(
          self,
          relative_file_path,
          force_children_retrieval=False):
    return self.get_child_file(
        relative_file_path,
        force_children_retrieval) is not None

  def relative_path_is_a_child(
          self,
          relative_path,
          force_children_retrieval=False):
    return (
        self.relative_path_is_a_file(
            relative_path,
            force_children_retrieval) or self.relative_path_is_a_folder(
            relative_path,
            force_children_retrieval))

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
    result = (
        f"Folder - {self.path[1:]}\n"
        f"  name                            = {self.name}\n"
        f"  id                              = {self.ms_id}\n"
        f"  size                            = {self.size}\n"
        f"  childcount                      = {self.child_count}\n"
        f"  lastModifiedDateTime            = {self.last_modified_datetime}\n"
        f"  creationDateTime                = {self.creation_datetime}\n"
        f"  childrenFilesRetrievalStatus    = {self.__children_files_retrieval_status}\n"
        f"  childrenFoldersRetrievalStatus  = {self.__children_folders_retrieval_status}\n")

    return result

  def __repr__(self):
    return f"Folder({self.name})"


class MsFileInfo(MsObject):
  def __init__(
          self, name, parent_path, mgc, file_id,
          size, qxh, s1h, cdt, lmdt, parent=None):
    # qxh = quickxorhash
    super().__init__(parent, name, parent_path, file_id, size)
    self.mgc = mgc
    self.sha1hash = s1h
    self.qxh = qxh
    self.creation_datetime = cdt
    self.last_modified_datetime = lmdt

  def _get_id(self):
    return self.__id
  id = property(_get_id)

  def __str__(self):
    fname = f"{self.name}" if len(self.name) < 45 else f"{self.name[:40]}..."
    fmdt = self.last_modified_datetime.strftime("%Y-%m-%d %H:%M:%S")
    result = f"{self.size:>20,}  {fname:<45}  {fmdt}  "
    return result

  def str_full_details(self):
    result = (
        f"File - '{self.name}'\n"
        f"  name                  = {self.name}\n"
        f"  full_path             = {self.path}\n"
        f"  id                    = {self.ms_id:>20}\n"
        f"  size                  = {self.size:,}\n"
        f"  quickXorHash          = {self.qxh}\n"
        f"  sha1Hash              = {self.sha1hash}\n"
        f"  creationDateTime      = {self.creation_datetime}\n"
        f"  lastModifiedDateTime  = {self.last_modified_datetime}"
    )

    return result

  def __repr__(self):
    return f"File({self.name})"


class ObjectInfoFactory:

  @staticmethod
  def get_object_info(mgc,
                      path,
                      parent=None,
                      no_warn_if_no_parent=False) -> Tuple[object,
                                                           Optional[MsObject]]:
    """
      Return a 2-tuple (<error_code>, <object_info>).
      If error_code is not None, object is None and error_code is set code of response sent by Msgraph.
      Else, object_info is set with found object or None if nothing is found.
    """
    if len(
            path) > 1 and path[0] == "/":  # Convert relative path in absolute path
      path = path[1:]
    # Consider root
    prefixed_path = "" if path == "/" or path == "" else f":/{path}"
    r = mgc.mgc.get(
        f'{MsGraphClient.graph_url}/me/drive/root{prefixed_path}').json()
    if 'error' in r:
      return (r['error']['code'], None)

    if ('folder' in r):
      # import pprint
      # pprint.pprint(mgc_response_json)
      mso = ObjectInfoFactory.MsFolderFromMgcResponse(
          mgc, r, parent, no_warn_if_no_parent=no_warn_if_no_parent)
    else:
      mso = ObjectInfoFactory.MsFileInfoFromMgcResponse(
          mgc, r, parent, no_warn_if_no_parent=no_warn_if_no_parent)
    return (None, mso)

  @staticmethod
  def MsFolderFromMgcResponse(
          mgc,
          mgc_response_json,
          parent=None,
          no_warn_if_no_parent=False):

    # Workaround following what seems to be a bug. Space is replaced by "%20" sequence
    #   in mgc_response when parent name contains a space
    if parent is not None:
      parent_path = parent.path
      is_root = False
    else:
      if not no_warn_if_no_parent:
        lg.warning(
            "[MsFolderFromMgcResponse]No parent folder to create a folder info")
      if 'parentReference' in mgc_response_json and 'path' in mgc_response_json[
              'parentReference']:
        parent_path = mgc_response_json['parentReference']['path'][12:]
        is_root = False
      else:
        parent_path = ""
        is_root = True

    #full_path = "" if "root" in mgc_response_json else f"{parent_path}/{mgc_response_json['name']}"
    result = MsFolderInfo(
        parent_path=parent_path,
        name=mgc_response_json['name'],
        mgc=mgc,
        id=mgc_response_json['id'],
        child_count=mgc_response_json['folder']['childCount'],
        size=mgc_response_json['size'],
        parent=parent,
        lmdt=str_from_ms_datetime(mgc_response_json['lastModifiedDateTime']),
        cdt=str_from_ms_datetime(mgc_response_json['createdDateTime']),
        is_root=is_root
    )
    if parent is not None:
      parent._MsFolderInfo__add_folder_info_if_necessary(result)
    return result

  @staticmethod
  def MsFileInfoFromMgcResponse(
          mgc,
          mgc_response_json,
          parent=None,
          no_warn_if_no_parent=False):
    if parent is None and not no_warn_if_no_parent:
      lg.warning(
          "[MsFileFromMgcResponse]No parent folder to create a file info")
    if 'quickXorHash' in mgc_response_json['file']['hashes']:
      qxh = mgc_response_json['file']['hashes']['quickXorHash']
    else:
      qxh = None
    result = MsFileInfo(mgc_response_json['name'],
                        mgc_response_json['parentReference']['path'][13:],
                        mgc,
                        mgc_response_json['id'],
                        mgc_response_json['size'],
                        qxh,
                        mgc_response_json['file']['hashes']['sha1Hash'],
                        str_from_ms_datetime(mgc_response_json['createdDateTime']),
                        str_from_ms_datetime(mgc_response_json['lastModifiedDateTime']),
                        parent=parent)

    if parent is not None:
      parent._MsFolderInfo__add_file_info_if_necessary(result)
    return result
