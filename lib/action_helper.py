from lib.check_helper import quickxorhash
from lib.shell_helper import MsFolderInfo
from lib.bulk_helper import bulk_folder_download


def action_get_user(mgc):
  user = mgc.get_user()
  print(
      "Display Name      = {0}\n"
      "userPrincipalName = {1}".format(
          user["displayName"],
          user["userPrincipalName"]
      ))


def action_get_children(mgc):
  folder_info = mgc.get_folder_info(args["<folder>"])
  children = folder_info.print_children()


def action_upload(mgc, remote_folder, src_file):
  # Upload a file
  mgc.put_file_content(
      remote_folder,
      src_file
  )


def action_raw_cmd(mgc):
  while True:
    my_input = input("your command (or quit):")
    if my_input == "quit":
      break
    result = mgc.raw_command(my_input)
    print(result)
    print(result.json())
    print("  ")


def action_download(mgc, remote_file, dst_local_path):
  r = mgc.download_file_content(
      remote_file,
      dst_local_path
  )


def action_mdownload(mgc, folder_path, dest_path, max_depth):
  mgc.logger.log_debug("action_mdownload - folder = '{0}' - depth = '{1}'".format(
      folder_path, max_depth
  ))
  bulk_folder_download(mgc, folder_path, dest_path, max_depth)


def action_remove(mgc, file_path):
  r = mgc.delete_file(file_path)
  exit(r)


def action_get_info(mgc, remote_path):
  r = mgc.get_object_info(remote_path)
  print(r[1].str_full_details())


def action_browse(mgc):
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


def action_qxh(src_file):
  qxh = quickxorhash()
  print(qxh.quickxorhash(src_file))
