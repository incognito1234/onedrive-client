
"""Onedrive Client Program

  Usage:
    odc init
    odc upload <srcfile> <dstremotefolder> [--logfile=<logfile>]
    odc get_user [--logfile=<logfile>]
    odc get_children <folder>
    odc raw_cmd
    odc browse [--logfile=<logfile>]
    odc download <remotefile> <dstlocalpath> [--logfile=<logfile>]
    odc get_info  <dstremotepath>
    odc qxh <srcfile>

  Options:
    <srcfile>          Source file
    <dstremotefolder>  Destination folder
    <remotefile>       Remote file
    <dstlocalpath>     Destination local path (folder or file)
    <dstremotepath>    Destination remote path (folder or file)
"""
from lib.auth_helper import get_sign_in_url, get_token_from_code, TokenRecorder
from lib.graph_helper import MsGraphClient

import pprint
from docopt import docopt
from lib.log import Logger
from lib.action_helper import action_get_user, action_get_children, action_upload, action_raw_cmd, action_download, action_get_info, action_browse, action_qxh
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
    action_get_user(mgc)

  if args["get_children"]:
    action_get_children(mgc)

  if args["upload"]:
    action_upload(mgc, args["<dstremotefolder>"], args["<srcfile>"])

  if args["raw_cmd"]:
    action_raw_cmd(mgc)

  if args["download"]:
    action_download(mgc, args["<remotefile>"], args["<dstlocalpath>"])

  if args["get_info"]:
    action_get_info(mgc, args["<dstremotepath>"])

  if args["browse"]:
    action_browse(mgc)

  if args["qxh"]:
    action_qxh(args["<srcfile>"])
