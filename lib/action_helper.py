from lib.check_helper import quickxorhash
from lib.shell_helper import MsFolderInfo
from lib.bulk_helper import bulk_folder_download, bulk_folder_upload
from beartype import beartype
from lib.graph_helper import MsGraphClient


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
  folder_info = mgc.get_object_info(folder)[1]
  folder_info.retrieve_children_info(recursive=False, depth=0)
  folder_info.print_children()


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
  exit(r)


@beartype
def action_get_info(mgc: MsGraphClient, remote_path: str):
  r = mgc.get_object_info(remote_path)
  print(r[1].str_full_details())


@beartype
def action_browse(mgc: MsGraphClient):
  # current_folder_info = mgc.get_folder_info("")
  current_folder_info = MsFolderInfo("", "", mgc)
  while True:

    if current_folder_info.parent is not None:
      print("  0 - <parent>")

    current_folder_info.print_children(start_number=1)

    my_input = input("your command (or quit): ")

    if my_input == "quit":
      break

    if my_input.isdigit() and int(my_input) <= len(
            current_folder_info.children_folder):

      int_input = int(my_input)
      if int_input == 0:
        current_folder_info = current_folder_info.parent
      else:

        current_folder_info = current_folder_info.children_folder[int(
            my_input) - 1]

    else:
      print("")
      print(">>>>> ERROR >>>>>>>> Invalid command <<<<<<<<<<<")
    print("")


@beartype
def action_qxh(src_file: str):
  qxh = quickxorhash()
  print(qxh.quickxorhash(src_file))
