#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
from re import fullmatch
from lib.datetime_helper import str_from_ms_datetime
from abc import ABC, abstractmethod
from beartype import beartype


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

  def MsObjectFromMgcResponse(mgc, mgc_response_json):
    if ('folder' in mgc_response_json):
      # import pprint
      # pprint.pprint(mgc_response_json)
      result = MsFolderInfo.MsFolderFromMgcResponse(mgc, mgc_response_json)
      return result
    else:
      return MsFileInfo.MsFileInfoFromMgcResponse(mgc, mgc_response_json)


class MsFolderInfo(MsObject):

  def __init__(
          self,
          name,
          full_path,
          mgc,
          id=0,
          child_count=None,
          size=None,
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
        "[retrieve_children_info] {0} - only_folders = {1} - depth = {2}".format(
            self.get_full_path(), only_folders, depth))
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
        if isFolder:
          fi = MsFolderInfo.MsFolderFromMgcResponse(self.__mgc, c, self)
          self.add_folder_info(fi)
          if recursive:
            fi.retrieve_children_info(
                only_folders=only_folders,
                recursive=recursive,
                depth=depth - 1)

        elif not only_folders:
          fi = MsFileInfo.MsFileInfoFromMgcResponse(self.__mgc, c)
          self.add_file_info(fi)
        else:
          self.__mgc.Logger.log_info(
              "retrieve_children_info : UNKNOWN RESPONSE")

      self.__mgc.logger.log_debug(
          "[retrieve_children_info] {0} - setting retrieval status".format(self.get_full_path()))

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

  def print_children(self, start_number=0, recursive=False, depth=999):
    if not self.folders_have_been_retrieved():
      self.__mgc.logger.log_debug(
          "[print_children] folder_path = {0} - folders have not been retrieved".format(
              self.get_full_path()))
      self.retrieve_children_info(
          only_folders=False,
          recursive=recursive,
          depth=depth)
    i = start_number
    for c in self.children_folder:
      print("{0:>3} - {1}".format(
          i,
          c
      ))
      i = i + 1
    for c in self.children_file:
      print("{0:>3} - {1}".format(
          i,
          c
      ))
      i = i + 1

    if recursive and depth > 0:
      for c in self.children_folder:
        nb_children = c.print_children(
            start_number=i, recursive=False, depth=depth - 1)

        i += nb_children

    return i - start_number

  def __str__(self):
    if not self.folders_have_been_retrieved():
      result = "Folder - {0}/ ({1} - {2:,})".format(self.get_full_path()
                                                    [1:], self.child_count, self.size)
    else:
      result = "Folder - {0}/ ({1})- <ok>".format(self.get_full_path()
                                                  [1:], self.child_count)
    return result

  def MsFolderFromMgcResponse(mgc, mgc_response_json, parent=None):
    return MsFolderInfo(
        full_path="{0}/{1}".format(
            mgc_response_json['parentReference']['path'][12:],
            mgc_response_json['name']),
        name=mgc_response_json['name'],
        mgc=mgc,
        id=mgc_response_json['id'],
        child_count=mgc_response_json['folder']['childCount'],
        size=mgc_response_json['size'],
        parent=parent
    )

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
    result = "File - {0:35} - {1:>25} - {2:>20,} - {3}".format(
        self.path,
        self.__id,
        self.size,
        self.last_modified_datetime
    )
    return result

  def MsFileInfoFromMgcResponse(mgc, mgc_response_json):
    if 'quickXorHash' in mgc_response_json['file']['hashes']:
      qxh = mgc_response_json['file']['hashes']['quickXorHash']
    else:
      qxh = None
    return MsFileInfo(mgc_response_json['name'],
                      mgc_response_json['parentReference']['path'][13:],
                      mgc,
                      mgc_response_json['id'],
                      mgc_response_json['size'],
                      qxh,
                      mgc_response_json['file']['hashes']['sha1Hash'],
                      str_from_ms_datetime(mgc_response_json['fileSystemInfo']['createdDateTime']),
                      str_from_ms_datetime(mgc_response_json['fileSystemInfo']['lastModifiedDateTime'])
                      )

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
