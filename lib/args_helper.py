
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
  sub_parsers = parser.add_subparsers(dest='command')

  parser_init = sub_parsers.add_parser('init', help='init token')

  parser_upload = sub_parsers.add_parser('upload', help='upload a file')
  parser_upload.add_argument('srcfile', type=str, help='source file')
  parser_upload.add_argument('dstpath', type=str, help='destination path')

  parser_raw_cmd = sub_parsers.add_parser('raw_cmd', help='raw command')

  parser_get_user = sub_parsers.add_parser('get_user', help='get user')

  parser_browse = sub_parsers.add_parser(
      'browse', help='browse from root folder')

  parser_download = sub_parsers.add_parser('download', help='download a file')
  parser_download.add_argument('remotefile', type=str, help='remote file')
  parser_download.add_argument(
      'dstlocalpath',
      type=str,
      help='destination path where file will be downloaded')

  parser_get_info = sub_parsers.add_parser(
      'get_info', help='get info from object')
  parser_get_info.add_argument(
      'dstremotepath',
      type=str,
      help='destination object')
  result = parser.parse_args()

  return result
