#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
import os
from lib.shell_helper import MsFolderInfo, MsFileInfo
from lib.check_helper import quickxorhash
from beartype import beartype
from lib.graph_helper import MsGraphClient
from lib.oi_factory import ObjectInfoFactory

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
  folder_info = ObjectInfoFactory.get_object_info(mgc, folder_path)[1]
  folder_info.retrieve_children_info(recursive=True, depth=max_depth)
  mdownload_folder(mgc, folder_info, dest_path, depth=max_depth)


@beartype
def mdownload_folder(
        mgc: MsGraphClient,
        ms_folder: MsFolderInfo,
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


@beartype
def bulk_folder_upload(
        mgc: MsGraphClient,
        src_local_path: str,
        dst_remote_folder: str,
        max_depth: int = 999):
  mgc.logger.log_debug(
      "[bulk_folder_upload]src_local_path = '{0}' - dst_remote_folder = {1} - depth = '{2}'".format(
          src_local_path, dst_remote_folder, max_depth))
  remote_object = ObjectInfoFactory.get_object_info(mgc, dst_remote_folder)
  if remote_object[0]:
    mgc.logger.log_error(
        "[bulk_folder_upload]folder '{0}' does not exist - Please create it first".format(dst_remote_folder))
    return False

  remote_folder_info = remote_object[1]
  if not isinstance(remote_folder_info, MsFolderInfo):
    mgc.logger.log_error(
        "[bulk_folder_upload]{0} exists but is not a folder - stop upload".format(dst_remote_folder))
    return False
  remote_folder_info.retrieve_children_info(recursive=True, depth=max_depth)
  mupload_folder(mgc, remote_folder_info, src_local_path, depth=max_depth)


@beartype
def mupload_folder(
        mgc: MsGraphClient,
        ms_folder: MsFolderInfo,
        src_path: str,
        depth: int = 999):
  mgc.logger.log_debug(
      '[mupload_folder]Starting. remote path = {0} - src path = {1} - depth = {2}'.format(
          ms_folder.get_full_path(), src_path, depth))
  ms_folder.retrieve_children_info(recursive=True, depth=depth)
  scan_dir = os.scandir(src_path)
  for entry in scan_dir:

    if entry.is_file():
      if ms_folder.is_child_folder(entry.name):
        mgc.logger.log_warning(
            '[mupload_folder]{0} is a local file but is a remote folder. Skip it'.format(
                entry.path()))
      else:
        if file_needs_upload(src_path, entry.name, ms_folder):
          mgc.logger.log_info(
              "[mupload_folder]Upload file {0}".format(
                  entry.path))
          mgc.put_file_content(ms_folder.get_full_path(),
                               "{0}/{1}".format(src_path, entry.name))

    elif entry.is_dir():

      if ms_folder.is_direct_child_file(entry.name):
        mgc.logger.log_warning(
            '[mupload_folder]{0} is a local folder but is a remote file. Skip it'.format(
                entry.path))
      else:
        sub_folder_info = ms_folder.get_child_folder(entry.name)
        if sub_folder_info is None:
          mgc.logger.log_info(
              '[mupload_folder]{0} does not exist. Create it'.format(
                  entry.path))
          sub_folder_info = ms_folder.create_empty_subfolder(entry.name)

        if depth > 0:
          mupload_folder(mgc, sub_folder_info, entry.path, depth - 1)
        else:
          mgc.logger.log_info(
              '[mupload_folder]maxdepth is reach for folder {0}. Stop recursive upload'.format(
                  entry.path))

    else:
      mgc.logger.log_warning('[mupload_folder]{0} is nothing 8-/ Skip it')

  scan_dir.close()

  return True


@beartype
def file_needs_upload(
        src_folder_path: str,
        str_file_name: str,
        ms_remote_folder: MsFolderInfo):
  str_local_file_name = "{0}/{1}".format(src_folder_path, str_file_name)

  if ms_remote_folder.is_direct_child_file(str_file_name):
    hash_qxh = qxh.quickxorhash(str_local_file_name)
    ms_fileinfo = ms_remote_folder.get_direct_child_file(str_file_name)

    if ms_fileinfo.qxh is not None:
      ms_fileinfo.mgc.logger.log_debug(
          "[file_needs_upload]qxh exists for '{0}' - '{1}' vs '{2}'".format(
              ms_fileinfo.name, hash_qxh, ms_fileinfo.qxh))
      result = ms_fileinfo.qxh != hash_qxh
    else:
      result = True
  else:
    result = True
  return result
