
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
  sub_parsers = parser.add_subparsers(dest='command')

  parser_init = sub_parsers.add_parser('init', help='init token')

  parser_upload = sub_parsers.add_parser('upload', help='upload a file')
  parser_upload.add_argument('srcfile', type=str, help='source file')
  parser_upload.add_argument('dstpath', type=str, help='destination path')

  parser_mupload = sub_parsers.add_parser(
      'mupload', help='upload a complete folder')
  parser_mupload.add_argument(
      'srclocalpath',
      type=str,
      help='source local folder')
  parser_mupload.add_argument(
      'dstremotefolder',
      type=str,
      help='destination remote folder')

  parser_raw_cmd = sub_parsers.add_parser('raw_cmd', help='raw command')

  parser_get_user = sub_parsers.add_parser('get_user', help='get user')

  parser_get_children = sub_parsers.add_parser(
      'get_children', help='get children')
  parser_get_children.add_argument('folder', type=str, help='folder')

  parser_browse = sub_parsers.add_parser(
      'browse', help='browse from root folder')

  parser_download = sub_parsers.add_parser('download', help='download a file')
  parser_download.add_argument('remotefile', type=str, help='remote file')
  parser_download.add_argument(
      'dstlocalpath',
      type=str,
      help='destination path where file will be downloaded')

  parser_mdownload = sub_parsers.add_parser(
      'mdownload', help='download a complete folder')
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

  parser_get_info = sub_parsers.add_parser(
      'get_info', help='get info from object')
  parser_get_info.add_argument(
      'dstremotepath',
      type=str,
      help='destination object')

  parser_remove = sub_parsers.add_parser(
      'remove',
      help='remove a file',
      description='Return 1 = OK. 0 = KO. 2 = Unknown')
  parser_remove.add_argument('filepath', type=str, help='remote file')

  parser_quickxorhash = sub_parsers.add_parser(
      'qxh', help='compute quickxorhash of file')
  parser_quickxorhash.add_argument('srcfile', type=str, help='source file')

  result = parser.parse_args()

  return result
