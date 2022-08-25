#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
from lib.check_helper import quickxorhash
from lib.shell_helper import OneDriveShell, LsFormatter, MsFolderFormatter, MsFileFormatter
from lib.bulk_helper import bulk_folder_download, bulk_folder_upload
from lib.oi_factory import ObjectInfoFactory
from beartype import beartype
from lib.graph_helper import MsGraphClient
import os


def action_get_user(mgc):
  user = mgc.get_user()
  print(
      "Display Name      = {0}\n"
      "userPrincipalName = {1}".format(
          user["displayName"],
          user["userPrincipalName"]
      ))


@beartype
def action_get_children(mgc: MsGraphClient, folder: str):
  folder_info = ObjectInfoFactory.get_object_info(mgc, folder)[1]
  folder_info.retrieve_children_info(recursive=False, depth=0)
  ls_formatter = LsFormatter(MsFileFormatter(60), MsFolderFormatter(60), False)
  ls_formatter.print_folder_children(folder_info, only_folders=False)


@beartype
def action_upload(mgc: MsGraphClient, remote_folder: str, src_file: str):
  # Upload a file
  mgc.put_file_content(
      remote_folder,
      src_file
  )


@beartype
def action_mupload(
        mgc: MsGraphClient,
        src_local_path: str,
        dst_remote_folder: str):
  mgc.logger.log_debug("action_mupload - folder = '{0}' to '{1}'".format(
      src_local_path, dst_remote_folder
  ))
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
  mgc.logger.log_debug("action_mdownload - folder = '{0}' - depth = '{1}'".format(
      folder_path, max_depth
  ))
  bulk_folder_download(mgc, folder_path, dest_path, max_depth)


@beartype
def action_remove(mgc: MsGraphClient, file_path: str):
  r = mgc.delete_file(file_path)
  return r


@beartype
def action_get_info(mgc: MsGraphClient, remote_path: str):
  r = ObjectInfoFactory.get_object_info(mgc, remote_path)
  print(r[1].str_full_details())


@beartype
def action_browse(mgc: MsGraphClient):
  od_shell = OneDriveShell(mgc)
  od_shell.launch()


@beartype
def action_mkdir(mgc: MsGraphClient, remote_folder: str):
  part_path = os.path.split(remote_folder)
  r = mgc.create_folder(part_path[0], part_path[1])
  if r is not None:
    mgc.logger.log_info(f"action_mkdir - folder {r} has just been create")
  else:
    mgc.logger.log_error(
        f"action_mkdir - error during creation folder {remote_folder}")
  return r


@beartype
def action_qxh(src_file: str):
  qxh = quickxorhash()
  print(qxh.quickxorhash(src_file))
