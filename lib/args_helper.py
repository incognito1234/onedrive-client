#  Copyright 2019-2023 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details


import argparse
import sys
from lib._common import get_versionned_name


def parse_odc_args(default_action):
  parser = argparse.ArgumentParser(
      prog='odc',
      description=get_versionned_name(),
      allow_abbrev=True)
  parser.add_argument(
      '--logfile',
      '-l',
      type=str,
      help='log file',
      default=None)
  parser.add_argument(
      '--forcenostderr',
      help='disable error logging on stderr if logging is not configured',
      action="store_true",
      default=False)
  parser.add_argument(
      '--logstdout',
      help='print log to stdout',
      action="store_true",
      default=False)
  parser.add_argument(
      '--loglevel',
      type=int,
      help='log level (default = WARN)',
      default=2)
  parser.set_defaults(command="")
  sub_parsers = parser.add_subparsers(dest='cmd')

  parser_init = sub_parsers.add_parser('init', help='init connexion')
  parser_init.set_defaults(command="init")

  parser_upload = sub_parsers.add_parser(
      'put', help='upload a file')
  parser_upload.add_argument(
      '--withprogressbar',
      help='add a progress bar',
      action="store_true",
      default=False)
  parser_upload.add_argument('srcfile', type=str, help='source file')
  parser_upload.add_argument('dstpath', type=str, help='destination path')
  parser_upload.set_defaults(command="put")

  parser_mupload = sub_parsers.add_parser(
      'mput', help='upload a complete folder')
  parser_mupload.add_argument(
      'srclocalpath',
      type=str,
      help='source local folder')
  parser_mupload.add_argument(
      'dstremotefolder',
      type=str,
      help='destination remote folder')
  parser_mupload.set_defaults(command="mput")

  parser_get_user = sub_parsers.add_parser('whoami', help='get user')
  parser_get_user.set_defaults(command="whoami")

  parser_get_children = sub_parsers.add_parser(
      'ls', help='list a folder content')
  parser_get_children.add_argument(
      'folder', type=str, help='folder to be listed')
  parser_get_children.add_argument(
      '-p',
      action="store_true",
      default=False,
      help='enable pagination')
  parser_get_children.add_argument(
      '-l',
      action="store_true",
      default=False,
      help='long format')
  parser_get_children.set_defaults(command="ls")

  parser_browse = sub_parsers.add_parser(
      'shell', help='interaction shell')
  parser_browse.set_defaults(command="shell")

  parser_download = sub_parsers.add_parser(
      'get', help='download a file')
  parser_download.add_argument('remotefile', type=str, help='remote file')
  parser_download.add_argument(
      'dstlocalpath',
      type=str,
      help='destination path where file will be downloaded')
  parser_download.set_defaults(command="get")

  parser_mdownload = sub_parsers.add_parser(
      'mget', help='download a complete folder')
  parser_mdownload.add_argument(
      'remotefolder',
      type=str,
      help='folder to be downloaded')
  parser_mdownload.add_argument(
      'dstlocalpath',
      type=str,
      help='local destination path')
  parser_mdownload.add_argument(
      '--depth',
      '-d',
      type=int,
      help='maximum depth',
      default=999)
  parser_mdownload.add_argument(
      '-n',
      action="store_true",
      default=False,
      help='skip warning if no-file-or-folder object are found (as Notebook)')
  parser_mdownload.set_defaults(command="mget")

  parser_get_info = sub_parsers.add_parser(
      'stat', help='get info from object')
  parser_get_info.add_argument(
      'dstremotepath',
      type=str,
      help='destination object')
  parser_get_info.set_defaults(command="stat")

  parser_share = sub_parsers.add_parser(
      'share', help='share a file or a folder')
  parser_share.add_argument('path', type=str, help='path to be shared')
  parser_share.set_defaults(command="share")

  parser_move = sub_parsers.add_parser(
      'mv', help='move a file or a folder')
  parser_move.add_argument('srcpath', type=str, help='source path')
  parser_move.add_argument('dstpath', type=str, help='destination path')
  parser_move.set_defaults(command="mv")

  parser_remove = sub_parsers.add_parser(
      'rm',
      help='remove a file',
      description='Return 1 = OK. 0 = KO. 2 = Unknown')
  parser_remove.add_argument('filepath', type=str, help='remote file')
  parser_remove.set_defaults(command="rm")

  parser_mkdir = sub_parsers.add_parser('mkdir', help='make a folder')
  parser_mkdir.add_argument(
      'remotefolder',
      type=str,
      help='Folder to be created')
  parser_mkdir.set_defaults(command="mkdir")

  parser_quickxorhash = sub_parsers.add_parser(
      'qxh', help='compute quickxorhash of file')
  parser_quickxorhash.add_argument('srcfile', type=str, help='source file')
  parser_quickxorhash.set_defaults(command="qxh")

  parser_raw_cmd = sub_parsers.add_parser('raw_cmd', help="raw command")
  parser_raw_cmd.set_defaults(command="raw_cmd")

  parser_version = sub_parsers.add_parser(
      'version', help="print version number")
  parser_version.set_defaults(command="version")

  if len(sys.argv) == 1:  # Default action
    sys.argv.append(default_action)

  result = parser.parse_args()

  return result
