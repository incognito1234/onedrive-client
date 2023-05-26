#  Copyright 2019-2023 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
import logging
import getpass

from lib.check_helper import quickxorhash
from lib.shell_helper import OneDriveShell, LsFormatter, MsFolderFormatter, MsFileFormatter
from lib.msobject_info import ObjectInfoFactory
from lib.bulk_helper import bulk_folder_download, bulk_folder_upload
from beartype import beartype
from lib.graph_helper import MsGraphClient
import os

lg = logging.getLogger('odc.action')


def action_get_user(mgc):
  user = mgc.get_user()
  print(
      f"Display Name      = {user['displayName']}\n"
      f"userPrincipalName = {user['userPrincipalName']}"
  )


@beartype
def action_get_children(
        mgc: MsGraphClient,
        folder: str,
        with_pagination: bool,
        long_format: bool):
  # TODO Make column sizes adaptative
  folder_info = ObjectInfoFactory.get_object_info(
      mgc, folder, no_warn_if_no_parent=True)[1]
  folder_info.retrieve_children_info(recursive=False, depth=0)
  ls_formatter = LsFormatter(MsFileFormatter(60), MsFolderFormatter(60), False)
  if long_format:
    ls_formatter.print_folder_children_long(
        folder_info,
        only_folders=False,
        with_pagination=with_pagination)
  else:
    ls_formatter.print_folder_children_lite(folder_info,
        only_folders=False,
        with_pagination=with_pagination)


@beartype
def action_upload(
        mgc: MsGraphClient,
        remote_folder: str,
        src_file: str,
        with_progress_bar: bool):
  # Upload a file
  mgc.put_file_content(
      remote_folder,
      src_file,
      with_progress_bar=with_progress_bar
  )


@beartype
def action_mupload(
        mgc: MsGraphClient,
        src_local_path: str,
        dst_remote_folder: str):
  lg.debug(
      f"action_mupload - folder = '{src_local_path}' to '{dst_remote_folder}'")
  bulk_folder_upload(mgc, src_local_path, dst_remote_folder)


@beartype
def action_raw_cmd(mgc: MsGraphClient):
  while True:
    my_input = input("your command (or quit):")
    if my_input == "quit":
      break
    result = mgc.raw_command(my_input)
    print(result)
    print(result.json())
    print("  ")


@beartype
def action_download(mgc: MsGraphClient, remote_file: str, dst_local_path: str):
  r = mgc.download_file_content(
      remote_file,
      dst_local_path
  )


@beartype
def action_mdownload(
        mgc: MsGraphClient,
        folder_path: str,
        dest_path: str,
        max_depth: int):
  lg.debug(
      f"action_mdownload - folder = '{folder_path}' - depth = '{max_depth}'")
  bulk_folder_download(mgc, folder_path, dest_path, max_depth)


@beartype
def action_move(mgc: MsGraphClient, src_path: str, dst_path: str):
  return mgc.move_object(src_path, dst_path)


@beartype
def action_remove(mgc: MsGraphClient, file_path: str):
  r = mgc.delete_file(file_path)
  return r


@beartype
def action_get_info(mgc: MsGraphClient, remote_path: str):
  r = ObjectInfoFactory.get_object_info(
      mgc, remote_path, no_warn_if_no_parent=True)
  if r[0] is not None:
    print("Object not found")
  else:
    print(r[1].str_full_details())


@beartype
def action_share(mgc: MsGraphClient, path: str):
  pwd = None
  try:
    pwd = getpass.getpass("Password :")
  except Exception as error:
    print('ERROR while reading password', error)
  if pwd is None:
    return
  r = mgc.create_share_link(path, "view", pwd)
  if r is not None:
    print(f"'{path}' is accessible here possibly with a new password: {r}")
  else:
    print("Error during creation of link")


@beartype
def action_shell(mgc: MsGraphClient):
  od_shell = OneDriveShell(mgc)
  od_shell.launch()


@beartype
def action_mkdir(mgc: MsGraphClient, remote_folder: str):
  part_path = os.path.split(remote_folder)
  r = mgc.create_folder(part_path[0], part_path[1])
  if r is not None:
    lg.info(f"action_mkdir - folder {r} has just been create")
  else:
    lg.error(f"action_mkdir - error during creation folder {remote_folder}")
  return r


@beartype
def action_qxh(src_file: str):
  qxh = quickxorhash()
  print(qxh.quickxorhash(src_file))
