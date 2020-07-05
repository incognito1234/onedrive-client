from lib.datetime_helper import str_from_ms_datetime
from abc import ABC, abstractmethod


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
      result = MsFolderInfo(
          "{0}/{1}".format(
              mgc_response_json['parentReference']['path'][12:],
              mgc_response_json['name']),
          mgc,
          id=mgc_response_json['id'],
          child_count=mgc_response_json['folder']['childCount'],
          size=mgc_response_json['size']
      )
      return result
    else:
      return MsFileInfo(
          mgc_response_json['name'],
          mgc_response_json['parentReference']['path'][13:],
          mgc,
          mgc_response_json['id'],
          mgc_response_json['size'],
          mgc_response_json['file']['hashes']['quickXorHash'],
          str_from_ms_datetime(mgc_response_json['fileSystemInfo']['createdDateTime']),
          str_from_ms_datetime(mgc_response_json['fileSystemInfo']['lastModifiedDateTime']))


class MsFolderInfo(MsObject):

  def __init__(
          self,
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
    self.__mgc = mgc
    self.children_file = []
    self.children_folder = []
    self.parent = parent
    self.child_count = child_count
    self.size = size
    self.__children_retrieval_info = "only_name"

  def get_full_path(self):
    return self.__full_path
  path = property(get_full_path)

  def _get_id(self):
    return self.__id
  id = property(_get_id)

  def _get_name(self):
    return self.get_full_path()
  name = property(_get_name)

  def retrieve_children_info(self):
    if not self.children_has_been_retrieved():
      ms_response = self.__mgc.get_ms_response_for_children_folder_path(
          self.get_full_path())
      for c in ms_response:
        isFolder = 'folder' in c
        if isFolder:
          fi = MsFolderInfo("{0}/{1}".format(
              self.get_full_path(),
              c['name']),
              self.__mgc,
              id=c['id'],
              child_count=c['folder']['childCount'],
              size=c['size'],
              parent=self
          )
          self.add_folder(fi)
        else:
          fi = MsFileInfo(
              c['name'],
              self.path,
              self.__mgc,
              c['id'],
              c['size'],
              None,
              None,
              None)
          self.add_file(fi)

      self.close_init()

  def add_folder(self, folder_info):
    self.children_folder.append(folder_info)
    self.__children_retrieval_info = "child_in_progress"

  def add_file(self, file_info):
    self.children_file.append(file_info)
    self.__children_retrieval_info = "child_in_progress"

  def close_init(self):
    self.__children_retrieval_info = "children"

  def children_has_been_retrieved(self):
    return self.__children_retrieval_info == "children"

  def print_children(self, start_number=0):
    if not self.children_has_been_retrieved():
      self.retrieve_children_info()
    i = start_number
    for c in self.children_folder:
      print("{0:>3} - {1}".format(
          i,
          c
      ))
      i = i + 1
    for c in self.children_file:
      # print("{0:>3} - {1}".format(
      #   i,
      #   c
      # ))
      i = i + 1

  def __str__(self):
    if not self.children_has_been_retrieved():
      result = "Folder - {0}/ ({1} - {2:,})".format(self.get_full_path()
                                                    [1:], self.child_count, self.size)
    else:
      result = "Folder - {0}/ ({1})- <ok>".format(self.get_full_path()
                                                  [1:], self.child_count)
    return result

  def str_full_details(self):
    result = ("Folder {0}"
              "test").format(self.get_full_path()[1:])
    return result


class MsFileInfo(MsObject):
  def __init__(self, name, parent_path, mgc, file_id, size, qxh, cdt, lmdt):
    # qxh = quickxorhash
    self.mgc = mgc
    self.__name = name
    self.__parent_path = parent_path
    self.__id = file_id
    self.size = size
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
    result = "File - {0:35} - {1:>25} - {2:>20,}".format(
        self.name,
        self.__id,
        self.size
    )
    return result

  def str_full_details(self):
    result = (
        "File - '{0}'\n"
        "  name                  = {1}\n"
        "  full_path             = {2}\n"
        "  id                    = {3:>20}\n"
        "  size                  = {4:,}\n"
        "  quickXorHash          = {5}\n"
        "  creationDateTime      = {6}\n"
        "  lastModifiedDateTime  = {7}"
    ).format(
        self.name,
        self.name,
        self.path,
        self.__id,
        self.size,
        self.qxh,
        self.creation_datetime,
        self.last_modified_datetime)

    return result
