import os
from lib.shell_helper import MsFolderInfo, MsFileInfo
from lib.check_helper import quickxorhash
from beartype import beartype
from lib.graph_helper import MsGraphClient

qxh = quickxorhash()


@beartype
def bulk_folder_download(
        mgc: MsGraphClient,
        folder_path: str,
        dest_path: str,
        max_depth: int):
  mgc.logger.log_debug(
      "bulk_folder_download - folder = '{0}' - dest_path = {1} - depth = '{2}'".format(
          folder_path, dest_path, max_depth))
  folder_info = mgc.get_object_info(folder_path)[1]
  folder_info.retrieve_children_info(recursive=True, depth=max_depth)
  mdownload_folder(mgc, folder_info, dest_path, depth=max_depth)


def mdownload_folder(
        mgc: MsGraphClient,
        ms_folder: str,
        dest_path: str,
        depth: int = 999):
  if os.path.exists(dest_path) and not os.path.isdir(dest_path):
    mgc.logger.log_error(
        "[mdownload_folder] {0} exists and is not a folder - skipping".format(
            dest_path))
    return False

  elif not os.path.exists(dest_path):
    mgc.logger.log_info(
        "[mdownload_folder] {0} does not exists - create it".format(
            dest_path))
    os.mkdir(dest_path)

  for file_info in ms_folder.children_file:
    if file_needs_download(file_info, dest_path):
      mgc.logger.log_info("[mdownload_folder] download '{0}' in '{1}'".format(
          file_info.path, dest_path
      ))
      mgc.download_file_content(file_info.path, dest_path)
    else:
      mgc.logger.log_debug(
          "[mdownload_folder] no need to download '{0}' in '{1}'".format(
              file_info.path, dest_path))

  if depth > 1:
    for cf in ms_folder.children_folder:
      mdownload_folder(
          mgc, cf, "{0}/{1}".format(dest_path, cf.name), depth - 1)

  return True


@beartype
def file_needs_download(ms_fileinfo: MsFileInfo, dest_path: str):
  local_file_name = "{0}/{1}".format(dest_path, ms_fileinfo.name)

  result = False

  # Check if local file exists
  if not os.path.exists(local_file_name):
    result = True

  # Check from quickxorhash if possible
  if not result and ms_fileinfo.qxh is not None:
    hash_qxh = qxh.quickxorhash(local_file_name)
    ms_fileinfo.mgc.logger.log_debug(
        "[file_needs_download]qxh exists for '{0}' - '{1}' vs '{2}'".format(
            ms_fileinfo.name, hash_qxh, ms_fileinfo.qxh))
    result = hash_qxh != ms_fileinfo.qxh

  else:
    result = True

  ms_fileinfo.mgc.logger.log_debug("[file_needs_download] {1} - {0}".format(
      local_file_name, "True" if result else "False")
  )
  return result
