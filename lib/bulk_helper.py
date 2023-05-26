#  Copyright 2019-2023 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
import logging

import os
from lib.check_helper import quickxorhash
from beartype import beartype
from lib.graph_helper import MsGraphClient
from lib.msobject_info import (
    ObjectInfoFactory, MsFolderInfo, MsFileInfo)

try:
  from tqdm import tqdm
except Exception:
  tqdm = None


lg = logging.getLogger('odc.bulk')
qxh = quickxorhash()


@beartype
def bulk_folder_download(
        mgc: MsGraphClient,
        folder_path: str,
        dest_path: str,
        max_depth: int):
  lg.debug(
      f"bulk_folder_download - folder = '{folder_path}'"
      f" - dest_path = {dest_path} - depth = '{max_depth}'")
  remote_object = ObjectInfoFactory.get_object_info(
      mgc, folder_path, no_warn_if_no_parent=True)

  if remote_object[0]:
    lg.error(
        f"[bulk_folder_download]folder '{dest_path}' does not exist")
    return False
  folder_info = remote_object[1]
  if not isinstance(folder_info, MsFolderInfo):
    lg.error(
        f"[bulk_folder_download]'{dest_path}' is a file")
    return False

  folder_info.retrieve_children_info(recursive=True, depth=max_depth)
  mdownload_folder(mgc, folder_info, dest_path, depth=max_depth)


@beartype
def mdownload_folder(
        mgc: MsGraphClient,
        ms_folder: MsFolderInfo,
        dest_path: str,
        depth: int = 999,
        list_tqdm: list = []):
  if os.path.exists(dest_path) and not os.path.isdir(dest_path):
    lg.error(
        f"[mdownload_folder] {dest_path} exists and is not a folder"
        " - skipping")
    return False

  elif not os.path.exists(dest_path):
    lg.info(
        f"[mdownload_folder] {dest_path} does not exists - create it")
    os.mkdir(dest_path)

  if tqdm is not None:
    n_tqdm = tqdm(
        desc=ms_folder.name,
        total=ms_folder.size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        colour="green" if len(list_tqdm) == 0 else "",
        position=len(list_tqdm),
        leave=len(list_tqdm) == 0)

    list_tqdm.append(n_tqdm)

  for file_info in ms_folder.children_file:
    if file_needs_download(file_info, dest_path):
      lg.info(
          f"[mdownload_folder] download '{file_info.path}' in '{dest_path}'")
      mgc.download_file_content(
          file_info.path,
          dest_path,
          retry_if_throttled=True, list_tqdm=list_tqdm)
    else:
      lg.debug(
          f"[mdownload_folder] no need to download '{file_info.path}'"
          f" in '{dest_path}'")

      if tqdm is not None:
        for i in range(len(list_tqdm) - 1, -1, -1):
          t = list_tqdm[i]
          t.update(file_info.size)

  if depth > 1:
    for cf in ms_folder.children_folder:
      mdownload_folder(
          mgc, cf, f"{dest_path}/{cf.name}", depth - 1, list_tqdm)

      # last_tqdm.close()
      # time.sleep(2)

  if tqdm is not None:
    last_tqdm = list_tqdm[-1]
    last_tqdm.close()
    list_tqdm.pop()

  return True


@beartype
def file_needs_download(ms_fileinfo: MsFileInfo, dest_path: str):
  local_file_name = f"{dest_path}/{ms_fileinfo.name}"

  result = False

  # Check if local file exists
  if not os.path.exists(local_file_name):
    result = True

  # Check from quickxorhash if possible
  if not result and ms_fileinfo.qxh is not None:
    hash_qxh = qxh.quickxorhash(local_file_name)
    lg.debug(
        f"[file_needs_download]qxh exists for '{ms_fileinfo.name}'"
        f" - '{hash_qxh}' vs '{ms_fileinfo.qxh}'")
    result = hash_qxh != ms_fileinfo.qxh

  else:
    result = True

  lg.debug(
      f"[file_needs_download] {local_file_name}"
      f" - {'True' if result else 'False'}")
  return result


@beartype
def bulk_folder_upload(
        mgc: MsGraphClient,
        src_local_path: str,
        dst_remote_folder: str,
        max_depth: int = 999):
  lg.debug(
      f"[bulk_folder_upload]src_local_path = '{src_local_path}'"
      f" - dst_remote_folder = {dst_remote_folder} - depth = '{max_depth}'")
  remote_object = ObjectInfoFactory.get_object_info(
      mgc, dst_remote_folder, no_warn_if_no_parent=True)
  if remote_object[0]:
    lg.error(
        f"[bulk_folder_upload]folder '{dst_remote_folder}' does not exist"
        " - Please create it first")
    return False

  remote_folder_info = remote_object[1]

  if not isinstance(remote_folder_info, MsFolderInfo):
    lg.error(
        f"[bulk_folder_upload]{dst_remote_folder} exists but is not a folder"
        " - stop upload")
    return False
  remote_folder_info.retrieve_children_info(recursive=True, depth=max_depth)
  mupload_folder(mgc, remote_folder_info, src_local_path, depth=max_depth)


@beartype
def mupload_folder(
        mgc: MsGraphClient,
        ms_folder: MsFolderInfo,
        src_path: str,
        depth: int = 999):
  lg.debug(
      f"[mupload_folder]Starting. remote path = {ms_folder.path}"
      f" - src path = {src_path} - depth = {depth}")
  ms_folder.retrieve_children_info(recursive=True, depth=depth)
  scan_dir = os.scandir(src_path)
  for entry in scan_dir:

    if entry.is_file():
      if ms_folder.is_direct_child_folder(entry.name):
        lg.warning(
            f"[mupload_folder]{entry.path} is a local file but is"
            " a remote folder. Skip it")
      else:
        if file_needs_upload(src_path, entry.name, ms_folder):
          lg.info(f"[mupload_folder]Upload file {entry.path}")
          mgc.put_file_content(
              ms_folder.path, f"{src_path}/{entry.name}")

    elif entry.is_dir():

      if ms_folder.is_direct_child_file(entry.name):
        lg.warning(
            f"[mupload_folder]{entry.path} is a local folder but is a remote file."
            " Skip it")
      else:
        sub_folder_info = ms_folder.get_child_folder(entry.name)
        if sub_folder_info is None:
          lg.info(f"[mupload_folder]{entry.path} does not exist. Create it")
          sub_folder_info = ms_folder.create_empty_subfolder(entry.name)

        if depth > 0:
          mupload_folder(mgc, sub_folder_info, entry.path, depth - 1)
        else:
          lg.info(
              f"[mupload_folder]maxdepth is reach for folder {entry.path}."
              " Stop recursive upload")

    else:
      lg.warning('[mupload_folder]entry is nothing 8-/ Skip it')

  scan_dir.close()

  return True


@beartype
def file_needs_upload(
        src_folder_path: str,
        str_file_name: str,
        ms_remote_folder: MsFolderInfo):
  str_local_file_name = f"{src_folder_path}/{str_file_name}"

  if ms_remote_folder.is_direct_child_file(str_file_name):
    hash_qxh = qxh.quickxorhash(str_local_file_name)
    ms_fileinfo = ms_remote_folder.get_direct_child_file(str_file_name)

    if ms_fileinfo.qxh is not None:
      lg.debug(
          f"[file_needs_upload]qxh exists for '{ms_fileinfo.name}'"
          f" - '{hash_qxh}' vs '{ms_fileinfo.qxh}'")
      result = ms_fileinfo.qxh != hash_qxh
    else:
      result = True
  else:
    result = True
  return result
