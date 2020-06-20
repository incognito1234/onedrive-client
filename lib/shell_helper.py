
class MsFolderInfo:

  def __init__(self, full_path, mgc, child_count=None, size=None, parent=None):
    """
        Init folder info
        mgc   = MsGraphClient
    """
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
              child_count=c['folder']['childCount'],
              size=c['size'],
              parent=self
          )
          self.add_folder(fi)
        else:
          fi = MsFileInfo(c['name'], self.__mgc, c['id'], c['size'])
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
      result = "{0}/ ({1} - {2:,})".format(self.get_full_path()
                                           [1:], self.child_count, self.size)
    else:
      result = "{0}/ ({1})- <ok>".format(self.get_full_path()
                                         [1:], self.child_count)
    return result


class MsFileInfo:
  def __init__(self, name, mgc, file_id, size):
    self.name = name
    self.id = file_id
    self.size = size
    self.mgc = mgc

  def __str__(self):
    result = "{0:35} - {1:>25} - {2:>20,}".format(
        self.name,
        self.id,
        self.size
    )
    return result


# class MsFolderInfoFactory:

#   def FolderInfoFromFullPath(full_path, mgc, parent = None):
#     """ Build folder info from children info retrieved from ms graph
#     """
#     root_folder = MsFolderInfo(full_path, mgc, parent)
#     root_folder.get_folder_info()
#     return root_folder
