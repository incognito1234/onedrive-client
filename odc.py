
"""
  Onedrive Client Program
"""
from lib.auth_helper import get_sign_in_url, get_token_from_code, TokenRecorder
from lib.graph_helper import MsGraphClient

import pprint
from lib.log import Logger
from lib.args_helper import parse_odc_args
from lib.action_helper import action_get_user, action_get_children, action_upload, action_raw_cmd, action_download, action_get_info, action_browse, action_qxh
import os
import sys

if __name__ == '__main__':

  current_dirname = os.path.dirname(os.path.realpath(__file__))
  args = parse_odc_args()

  if args.logfile is not None:
    lg = Logger(args.logfile, Logger.LOG_LEVEL_DEBUG)
  else:
    lg = Logger(None, None)

  tr = TokenRecorder("{0}/.token.json".format(current_dirname), lg)

  if args.command == 'init':
    sign_in_url, state = get_sign_in_url()
    print("url = {}".format(sign_in_url))
    url = input("url callback: ")
    token = get_token_from_code(url, state)
    tr.store_token(token)
    quit()

  if not tr.token_exists():
    print("please connect first with {} init".format(sys.argv[0]))
    quit()

  mgc = MsGraphClient(tr.get_session_from_token(), lg)
  if args.command == "get_user":
    action_get_user(mgc)

  if args.command == "get_children":
    action_get_children(mgc)

  if args.command == "upload":
    action_upload(mgc, args.dstpath, args.srcfile)

  if args.command == "raw_cmd":
    action_raw_cmd(mgc)

  if args.command == "browse":
    action_browse(mgc)

  if args.command == "download":
    action_download(mgc, args.remotefile, args.dstlocalpath)

  if args.command == "get_info":
    action_get_info(mgc, args.dstremotepath)
