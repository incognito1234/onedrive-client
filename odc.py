#!../bin/python3
#  Copyright 2019-2023 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
"""
  Onedrive Client Program
"""
import logging
from lib.auth_helper import TokenRecorder
from lib.graph_helper import MsGraphClient

from lib.args_helper import parse_odc_args
from lib.action_helper import (
    action_get_user,
    action_get_children,
    action_upload, action_mupload,
    action_raw_cmd,
    action_download, action_mdownload,
    action_get_info, action_share,
    action_shell, action_qxh, action_move, action_remove,
    action_mkdir
)
from lib.file_config_helper import create_and_get_config_folder, force_permission_file_read_write_owner
import os
import sys
from lib._common import VERSION
from os.path import exists


def configure_logging(args):

  FORMAT_LOG = "%(asctime)-15s %(name)s [%(levelname)s] %(message)s"
  if exists(
          f"{os.path.dirname(os.path.realpath(__file__))}{os.sep}logging_config.py"):
    import logging_config

  else:
    # Default config
    logging.basicConfig(format=FORMAT_LOG)

    lg = logging.getLogger('odc')
    # logging level are given here:
    # https://docs.python.org/3.8/library/logging.html#levels
    lg.setLevel(50 - (args.loglevel * 10))

  # Config that can be forced with args
  lg_root = logging.getLogger()
  if not args.logstdout:
    if (len(lg_root.handlers) > 0):
      # Should be a StreamHandler that writes on std.err
      sh = lg_root.handlers[0]
      lg_root.removeHandler(sh)

  if args.forcenostderr:
    # By default, message error are logged on console if no handlers is configured.
    # The following line disables this behavior.
    logging.lastResort = logging.NullHandler()

  if args.logfile is not None:
    fh = logging.FileHandler(filename=args.logfile)
    fh.setFormatter(logging.Formatter(FORMAT_LOG))
    lg_root.addHandler(fh)


if __name__ == '__main__':

  args = parse_odc_args(default_action="shell")

  # Configure Logger
  configure_logging(args)

  # Get authentication token
  config_dirname = create_and_get_config_folder()
  if config_dirname is None:
    exit(0)

  token_file_name = f"{config_dirname}/.token.json"
  tr = TokenRecorder(token_file_name)

  if args.command == 'init':

    token_ok = tr.get_token_interactivaly(
        ("Enter the following URL in a browser"
         " and connect to your MS Account:\n\n"),
        ("\nAn error page should be displayed. \n"
         "Copy/Paste here the url which appears in the address bar: \n"))
    if token_ok:
      tr.store_token()
      print("initialization OK")
    else:
      print("error during initialization of token")
    quit()

  if os.path.exists(token_file_name):
    tr.init_token_from_file()
    tr.store_token()
    force_permission_file_read_write_owner(token_file_name)

  if not tr.token_exists():
    print(f"please connect first with {sys.argv[0]} init")
    quit()

  # Manage command
  mgc = MsGraphClient(tr.get_session_from_token())
  if args.command == "whoami":
    action_get_user(mgc)

  if args.command == "ls":
    # TODO Add a warning if listed folder has more than 200 elements
    # TODO Add a option to retrieved all elements
    action_get_children(mgc, args.folder, args.p, args.l)

  if args.command == "put":
    action_upload(mgc, args.dstpath, args.srcfile, args.withprogressbar)

  if args.command == "mput":
    action_mupload(mgc, args.srclocalpath, args.dstremotefolder)

  if args.command == "raw_cmd":
    action_raw_cmd(mgc)

  if args.command == "shell":
    action_shell(mgc)

  if args.command == "get":
    action_download(mgc, args.remotefile, args.dstlocalpath)

  if args.command == "mget":
    action_mdownload(
        mgc,
        args.remotefolder,
        args.dstlocalpath,
        args.depth,
        args.n,
        file_with_exclusion=None if args.X == '' else args.X
  )

  if args.command == "mv":
    action_move(mgc, args.srcpath, args.dstpath)

  if args.command == "rm":
    action_remove(mgc, args.filepath)

  if args.command == "stat":
    action_get_info(mgc, args.dstremotepath)

  if args.command == "share":
    action_share(mgc, args.path)

  if args.command == "mkdir":
    action_mkdir(mgc, args.remotefolder)

  if args.command == "qxh":
    action_qxh(args.srcfile)

  if args.command == "version":
    print(VERSION)

  mgc.close()
