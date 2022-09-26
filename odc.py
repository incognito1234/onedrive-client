#!../bin/python3
#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
"""
  Onedrive Client Program
"""
import logging

from lib.auth_helper import get_sign_in_url, get_token_from_code, TokenRecorder
from lib.graph_helper import MsGraphClient

import pprint
from lib.args_helper import parse_odc_args
from lib.action_helper import (
    action_get_user,
    action_get_children,
    action_upload, action_mupload,
    action_raw_cmd,
    action_download, action_mdownload,
    action_get_info,
    action_browse, action_qxh, action_move, action_remove,
    action_mkdir
)
from lib.file_config_helper import create_and_get_config_folder, force_permission_file_read_write_owner
import os
import sys

# TODO Implement configure logger from file

if __name__ == '__main__':

  args = parse_odc_args()

  # Configure Logger
  FORMAT_LOG = "%(asctime)-15s %(name)s [%(levelname)s] %(message)s"
  logging.basicConfig(format=FORMAT_LOG)
  lg_root = logging.getLogger()
  if not args.logstdout:
    if (len(lg_root.handlers) > 0):
      # Should be a StreamHandler that writes on std.err
      sh = lg_root.handlers[0]
      lg_root.removeHandler(sh)
    else:
      print("ERROR: No default logging hander has been detected")

  if args.forcenostderr:
    # By default, message error are logged on console if no handlers is configured.
    # The following line disables this behavior.
    logging.lastResort = logging.NullHandler()

  if args.logfile is not None:
    fh = logging.FileHandler(filename=args.logfile)
    fh.setFormatter(logging.Formatter(FORMAT_LOG))
    lg_root.addHandler(fh)

  lg = logging.getLogger('odc')
  # logging level are given here:
  # https://docs.python.org/3.8/library/logging.html#levels
  lg.setLevel(50 - (args.loglevel * 10))

  lg_odshell = logging.getLogger('odc.browser')
  lg_odshell.setLevel(logging.ERROR)
  lg_odshell.addHandler(logging.StreamHandler())

  # Get authentication token
  config_dirname = create_and_get_config_folder()
  if config_dirname is None:
    exit(0)

  token_file_name = "{0}/.token.json".format(config_dirname)
  force_permission_file_read_write_owner(token_file_name)
  tr = TokenRecorder(token_file_name)

  if args.command == 'init':
    sign_in_url, state = get_sign_in_url()
    print("url = {}".format(sign_in_url))
    url = input("url callback: ")
    token = get_token_from_code(url, state)
    tr.store_token(token)
    quit()
  else:
    tr.init_token_from_file()

  if not tr.token_exists():
    print("please connect first with {} init".format(sys.argv[0]))
    quit()

  # Manage command
  mgc = MsGraphClient(tr.get_session_from_token())
  if args.command == "get_user":
    action_get_user(mgc)

  if args.command == "ls":
    # TODO Add a warning if listed folder has more than 200 elements
    # TODO Add a option to retrieved all elements
    action_get_children(mgc, args.folder, args.p)

  if args.command == "put":
    action_upload(mgc, args.dstpath, args.srcfile)

  if args.command == "mput":
    action_mupload(mgc, args.srclocalpath, args.dstremotefolder)

  if args.command == "raw_cmd":
    action_raw_cmd(mgc)

  if args.command == "browse":
    action_browse(mgc)

  if args.command == "get":
    action_download(mgc, args.remotefile, args.dstlocalpath)

  if args.command == "mget":
    action_mdownload(mgc, args.remotefolder, args.dstlocalpath, args.depth)

  if args.command == "mv":
    action_move(mgc, args.srcpath, args.dstpath)

  if args.command == "rm":
    action_remove(mgc, args.filepath)

  if args.command == "stat":
    action_get_info(mgc, args.dstremotepath)

  if args.command == "mkdir":
    action_mkdir(mgc, args.remotefolder)

  if args.command == "qxh":
    action_qxh(args.srcfile)

  mgc.close()
