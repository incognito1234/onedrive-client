
"""Onedrive Client Program

  Usage:
    odc init
    odc upload <srcfile> <dstfolder> [--logfile=<logfile>]
    odc get_user
    odc get_children <folder>
    odc raw_cmd
    odc browse

  Options:
    <srcfile>    Source file
    <dstfolder>  Destination folder
"""
from lib.auth_helper import get_sign_in_url, get_token_from_code, TokenRecorder
from lib.graph_helper import MsGraphClient
import pprint
from docopt import docopt
from lib.shell_helper import MsFolderInfo
from lib.log import Logger
import os


if __name__ == '__main__':

  current_dirname = os.path.dirname(os.path.realpath(__file__))

  args = docopt(__doc__, version='mgcli 1.0')
  if args["--logfile"] is not None:
    lg = Logger(args["--logfile"], Logger.LOG_LEVEL_DEBUG)
  else:
    lg = Logger(None, None)

  tr = TokenRecorder("{0}/.token.json".format(current_dirname), lg)

  if args["init"]:
    sign_in_url, state = get_sign_in_url()
    print("url = {}".format(sign_in_url))
    url = input("url callback: ")
    token = get_token_from_code(url, state)
    tr.store_token(token)
    quit()

  if not tr.token_exists():
    print("please connect first with mgcli init")
    quit()

  mgc = MsGraphClient(tr.get_session_from_token(), lg)
  if args["get_user"]:
    user = mgc.get_user()
    print(
        "Display Name      = {0}\n"
        "userPrincipalName = {1}".format(
            user["displayName"],
            user["userPrincipalName"]
        ))

  if args["get_children"]:
    folder_info = mgc.get_folder_info(args["<folder>"])
    children = folder_info.print_children()

  if args["upload"]:
    # Upload a file

    r = mgc.put_file_content(
        args["<dstfolder>"],
        args["<srcfile>"]
    )

  if args["raw_cmd"]:

    while True:
      my_input = input("your command (or quit):")
      if my_input == "quit":
        break
      result = mgc.raw_command(my_input)
      print(result)
      print(result.json())
      print("  ")

  if args["browse"]:

    # current_folder_info = mgc.get_folder_info("")
    current_folder_info = MsFolderInfo("", mgc)
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


if 1 == 0:
  # Initialization of token
  tr = TokenRecorder("token.json")

  if tr.token_exists():
    pass
  else:
    sign_in_url, state = get_sign_in_url()
    print("url = {}".format(sign_in_url))
    url = input("url callback: ")
    token = get_token_from_code(url, state)
    tr.store_token(token)

  mgc = MsGraphClient(tr)

  # Export file list from one folder
  children = mgc.get_folder_children('Photos/201804-Ethiopie/')
  pf = open('output.txt', 'w')
  pp = pprint.PrettyPrinter(stream=pf, indent=2)
  pp.pprint(children)

  # Write file name
  i = 0
  for c in children:
    isFolder = 'folder' in c
    if not isFolder:
      filedescription = "{0} - {1:>20,}".format(c['id'], c['size'])

    print("{0:>3} : {1:>30}{2} {3}".format(
        i,
        c['name'],
        '/' if isFolder else "",
        "- {0}".format(filedescription) if not isFolder else ""))

    i = i + 1

  # Upload a file
  # r = mgc.put_file_content(
  #   '/Perso/largefile.tar.gz',
  #   '/home/xxxxxxxx/src/env_test_graph/src.tar.gz'
  # )
