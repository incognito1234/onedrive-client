#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details

"""Onedrive Client Program

  Usage:
    odc init
    odc upload <srcfile> <dstremotefolder>
    odc mupload <srclocalpath> <dstremotefolder>
    odc get_user
    odc get_children <folder>
    odc raw_cmd
    odc browse
    odc download <remotefile> <dstlocalpath>
    odc mdownload <folderpath> <dstlocalpath>
    odc remove <filepath>
    odc get_info  <dstremotepath>
    odc qxh <srcfile>

  Options:
    <srcfile>          Source file
    <dstremotefolder>  Destination folder
    <remotefile>       Remote file
    <dstlocalpath>     Destination local path (folder or file)
    <dstremotepath>    Destination remote path (folder or file)
"""

import argparse


def parse_odc_args():
  parser = argparse.ArgumentParser(
      prog='odc',
      description="OneDrive Client Program",
      allow_abbrev=True)
  parser.add_argument(
      '--logfile',
      '-l',
      type=str,
      help='log file',
      default=None)
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

  parser_init = sub_parsers.add_parser('init', help='init token')
  parser_init.set_defaults(command="init")

  parser_upload = sub_parsers.add_parser(
      'put', aliases=['upload'], help='upload a file')
  parser_upload.add_argument('srcfile', type=str, help='source file')
  parser_upload.add_argument('dstpath', type=str, help='destination path')
  parser_upload.set_defaults(command="put")

  parser_mupload = sub_parsers.add_parser(
      'mput', aliases=['mupload'], help='upload a complete folder')
  parser_mupload.add_argument(
      'srclocalpath',
      type=str,
      help='source local folder')
  parser_mupload.add_argument(
      'dstremotefolder',
      type=str,
      help='destination remote folder')
  parser_mupload.set_defaults(command="mput")

  parser_raw_cmd = sub_parsers.add_parser('raw_cmd', help='raw command')
  parser_raw_cmd.set_defaults(command="raw_cmd")

  parser_get_user = sub_parsers.add_parser('get_user', help='get user')
  parser_get_user.set_defaults(command="get_user")

  parser_get_children = sub_parsers.add_parser(
      'ls', aliases=['get_children'], help='get children')
  parser_get_children.add_argument('folder', type=str, help='folder')
  parser_get_children.set_defaults(command="ls")

  parser_browse = sub_parsers.add_parser(
      'browse', help='browse from root folder')
  parser_browse.set_defaults(command="browse")

  parser_download = sub_parsers.add_parser(
      'get', aliases=['download'], help='download a file')
  parser_download.add_argument('remotefile', type=str, help='remote file')
  parser_download.add_argument(
      'dstlocalpath',
      type=str,
      help='destination path where file will be downloaded')
  parser_download.set_defaults(command="get")

  parser_mdownload = sub_parsers.add_parser(
      'mget', aliases=['mdownload'], help='download a complete folder')
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
  parser_mdownload.set_defaults(command="mget")

  parser_get_info = sub_parsers.add_parser(
      'stat', aliases=['get_info'], help='get info from object')
  parser_get_info.add_argument(
      'dstremotepath',
      type=str,
      help='destination object')
  parser_get_info.set_defaults(command="stat")

  parser_move = sub_parsers.add_parser(
      'mv', aliases=['move'], help='move a file or a folder')
  parser_move.add_argument('srcpath', type=str, help='source path')
  parser_move.add_argument('dstpath', type=str, help='destination path')
  parser_move.set_defaults(command="mv")

  parser_remove = sub_parsers.add_parser(
      'rm',
      aliases=['remove'],
      help='remove a file',
      description='Return 1 = OK. 0 = KO. 2 = Unknown')
  parser_remove.add_argument('filepath', type=str, help='remote file')
  parser_remove.set_defaults(command="rm")

  parser_mkdir = sub_parsers.add_parser('mkdir', help='make a directory')
  parser_mkdir.add_argument(
      'remotefolder',
      type=str,
      help='folder to be created')
  parser_mkdir.set_defaults(command="mkdir")

  parser_quickxorhash = sub_parsers.add_parser(
      'qxh', help='compute quickxorhash of file')
  parser_quickxorhash.add_argument('srcfile', type=str, help='source file')
  parser_quickxorhash.set_defaults(command="qxh")

  result = parser.parse_args()

  return result
