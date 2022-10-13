#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
import logging

import math
import os
import re
import argparse
import subprocess
from platform import platform
from unittest import expectedFailure
from colorama import Fore, Style, init as cinit
from io import StringIO
from abc import ABC, abstractmethod
import sys
# readline introduce history management in prompt
import readline
import shlex
import pydoc
from abc import ABC, abstractmethod
import re
from lib._typing import List, Optional
from beartype import beartype

from lib.graph_helper import MsGraphClient
from lib.msobject_info import (
    MsFileInfo, MsFolderInfo, MsObject,
    ObjectInfoFactory as Oif, StrPathUtil)
from lib._common import PROGRAM_NAME, get_versionned_name

lg = logging.getLogger('odc.browser')


class CommonCompleter:
  """ Class to gather methods used in SubCompleter
  """

  @staticmethod
  def get_cmd_parts_with_quotation_guess(input):
    try:
      # WARNING: does not work with win32 if a backslash is included in input
      return shlex.split(input)

    except ValueError as e:
      try:
        return shlex.split(input + "'")

      except ValueError as e:
        return shlex.split(input + '"')
  pass

  @staticmethod
  def extract_raw_last_args(input, parsed_last_arg):
    """
      Extract raw last args (with quote and escape chars) from input line.
      parsed_last_args is the last argument without quote and escape chars.

      Return None if not found
    """
    # Build shlex to compute last arg
    s = shlex.shlex(punctuation_chars=" ")
    s.whitespace = "\t\r\n"
    s.quotes = ""
    s.escape = ""
    s.commenters = ''
    s.instream = StringIO(input)
    part_args = list(s)

    i = len(part_args) - 1
    raw_last_args = ""
    while i > 1:

      raw_last_args = part_args[i] + raw_last_args  # append last args to left
      part_std_shlex = CommonCompleter.get_cmd_parts_with_quotation_guess(
          raw_last_args)

      if len(part_std_shlex) > 0:
        last_arg_std_shlex = part_std_shlex[0]
      else:
        last_arg_std_shlex = ""

      if parsed_last_arg == last_arg_std_shlex:  # found !
        if part_args[i - 1][-1] != " ":
          raw_last_args = raw_last_args + part_args[i - 1]  # probably a quote
        return raw_last_args

      i = i - 1

   # self.__log_debug(f'extract_raw_last_args("{input}","{parsed_last_arg}")
   # not found')
    return None


class SubCompleter(ABC):

  class SCResult():
    """ SubCompleter Result

    :param str candidate:       What will replace the line once it will be chosen
    :param str to_be_displayed: What will be displayed
    """
    @beartype
    def __init__(self, candidate: str, to_be_displayed: str):

      self.candidate = candidate
      self.to_be_displayed = to_be_displayed

    def __repr__(self):
      return f"SCResult('{self.candidate}','{self.to_be_displayed}')"

  @beartype
  def __init__(self):
    pass

  @abstractmethod
  @beartype
  def values(self, text: str) -> List[SCResult]:
    """  Compute candidates and displayed values regarding the line

    :param str line: List of candidates and displayed values
    """
    pass


class SubCompleterFileOrFolder(SubCompleter):

  @beartype
  def __init__(self, ods: "OneDriveShell", only_folder: bool):
    super(self.__class__, self).__init__()
    self.ods = ods
    self.__only_folder = only_folder

  @beartype
  def values(self, text: str) -> List[SubCompleter.SCResult]:
    parts_cmd = CommonCompleter.get_cmd_parts_with_quotation_guess(text)

    if len(parts_cmd) > 1:
      last_arg = parts_cmd[-1]
      was_relative_path = len(last_arg) > 0 and last_arg[0] != '/'

      # lfip = last_folder_info_path   -  rt = remaining test
      (lfip, rt) = MsObject.get_lastfolderinfo_path(
          self.ods.root_folder, last_arg, self.ods.current_fi)
      if lfip is None:  # Non existing folder
        return []
      start_text = rt
      folder_names_str = lfip.path + '/'
      if was_relative_path and folder_names_str.startswith(
              self.ods.current_fi.path):
        folder_names_str = folder_names_str[(
            len(self.ods.current_fi.path) + 1):]
      search_folder = lfip
    else:
      start_text = ""
      folder_names_str = ""
      search_folder = self.ods.current_fi

    # Extract start of last arguments to be escaped if necessary. Other
    # arguments won't be changed
    if len(parts_cmd) > 1:
      raw_last_arg = CommonCompleter.extract_raw_last_args(text, parts_cmd[-1])
      start_line = text[:-(len(raw_last_arg))]
    else:  # len(parts_cmd) == 1
      start_line = text.rstrip() + " "

    new_start_line = start_line + StrPathUtil.escape_str(folder_names_str)

    # Compute list of substitute string
    #   1. Compute folder names
    #   2. Append '/' to all folders
    #   3. Keep folders whose name starts with start_text
    #   4. Add escaped folder name
    search_folder.retrieve_children_info(only_folders=self.__only_folder)
    if self.__only_folder:
      all_children = search_folder.children_folder
    else:
      all_children = search_folder.children_folder + search_folder.children_file
    folders = map(
        lambda x: f"{x.name}{'/' if isinstance(x, MsFolderInfo) else ''}",
        all_children)
    folders = filter(lambda x: x.startswith(start_text), folders)
    folders = map(lambda x: StrPathUtil.escape_str(x), folders)
    map_values = map(
        lambda x: SubCompleter.SCResult(
            f"{new_start_line}{x}", x), folders)
    list_values = list(map_values)
    return list_values


class SubCompleterLocalCommand(SubCompleter):
  """ SubCompleter for local command

    Based on the following snippets:
       https://gist.github.com/mkhon/ad39dd3e54dd783b63d4
  """
  RE_SPACE = re.compile('.*\\s+$', re.M)

  def __init__(self):
    super(self.__class__, self).__init__()
    self.builtins = None
    self.commands = {
        'foo': True,
        'bar': False,
    }
    self.cmd_lookup = None
    self.path_lookup = None

    # try to get shell builtins
    shell = os.environ.get('SHELL')
    if shell:
      p = subprocess.Popen([shell, '-c', 'compgen -b'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      out, err = p.communicate()
      self.builtins = dict((key.decode(), True) for key in out.split())
    if not self.builtins:
      self.builtins = {'cd': True}

  def _generate(self, prefix):
    def begins_with(s): return s[:len(prefix)] == prefix
    self.cmd_lookup = {}
    # lg.debug("Entering generate")

    # append commands in PATH
    for path in map(os.path.expanduser, os.environ.get('PATH', '').split(':')):
      if not os.path.isdir(path):
        continue

      for f in filter(begins_with, os.listdir(path)):
        self.cmd_lookup[f] = True

    # append shell builtins
    for n in filter(begins_with, self.builtins.keys()):
      self.cmd_lookup[n] = self.builtins[n]

    # append COMMANDS
    for n in filter(begins_with, self.commands.keys()):
      self.cmd_lookup[n] = self.commands[n]
    # print "\nGenerated commands for prefix %s: %s" % (`prefix`,
    # `self.cmd_lookup`)

  def _listdir(self, root):
    "List directory 'root' appending the path separator to subdirs."
    res = []
    for name in os.listdir(root):
      path = os.path.join(root, name)
      if os.path.isdir(path):
        name += os.sep
      res.append(name)
    return res

  def _complete_path(self, path=None):
    "Perform completion of filesystem path."
    if not path:
      return self._listdir('.')
    dirname, rest = os.path.split(path)
    tmp = dirname if dirname else '.'
    res = [os.path.join(dirname, p)
           for p in self._listdir(tmp) if p.startswith(rest)]
    # more than one match, or single match which does not exist (typo)
    if len(res) > 1 or not os.path.exists(path):
      return res
    # resolved to a single directory, so return list of files below it
    if os.path.isdir(path):
      return [os.path.join(path, p) for p in self._listdir(path)]
    # exact file match terminates this completion
    return [path + ' ']

  def values(self, text: str) -> List[SubCompleter.SCResult]:
    "Generic readline completion entry point."

    try:
      buffer = text[1:]  # remove first '!'
      text_part = buffer.split()
      # account for last argument ending in a space
      if text_part and SubCompleterLocalCommand.RE_SPACE.match(buffer):
        text_part.append('')

      last_arg = text_part[-1]
      # command completion
      if len(text_part) < 2:
        self._generate(last_arg)
        result = [c + ' ' for c in self.cmd_lookup.keys()]
        return list(map(lambda x: SubCompleter.SCResult(f"!{x}", x), result))

      else:
        # check if we should do path completion
        start_line = ' '.join(text_part[:-1])
        cmd = text_part[0]
        if not self.cmd_lookup:
          self._generate(cmd)
        if cmd not in self.cmd_lookup or not self.cmd_lookup[cmd]:
          return []
        result = self._complete_path(os.path.expanduser(last_arg))
        result = map(lambda x: StrPathUtil.escape_str(x), result)
        return list(
            map(
                lambda x: SubCompleter.SCResult(
                    f"!{start_line} {x}",
                    x),
                result))

    except Exception as e:
      lg.error(f"[subCompleter shell]Error '{e}'")


class SubCompleterNone(SubCompleter):
  def __init__(self):
    pass

  @beartype
  def values(self, line: str) -> List[SubCompleter.SCResult]:
    return []


class Completer:
  """
  Everything is replaced in the readline buffer to managed folder name with space

   To avoid misunderstanding, only the folder name is displayed in the match list
  """

  def __init__(self, odshell):
    self.shell = odshell
    self.values = []
    self.start_line = ""
    self.new_start_line = ""
    self.columns_printer = ColumnsPrinter(2)
    self.lg_complete = logging.getLogger("odc.browser.completer")

  def __log_debug(self, what):
    self.lg_complete.debug(f"[complete]{what}")

  def display_matches(self, what, matches, longest_match_length):
    try:
      self.__log_debug(f"[display matches]dm('{what}',{matches})")
      print("")

      # remove start_line from matches and convert to FormattedString
      to_be_printed = list(
          map(
              lambda x: FormattedString.build_from_string(
                  x.to_be_displayed),
              self.values))
      self.columns_printer.print_with_columns(to_be_printed)
      print(
          f"{self.shell.get_prompt()}{readline.get_line_buffer()}",
          end="",
          flush=True)

    except Exception as e:
      print(f"Exception = {e}")

  @beartype
  def complete(self, text: str, state: int):

    self.__log_debug(f"complete('{text}',{state})")

    try:

      if state == 0:
        parts_cmd = CommonCompleter.get_cmd_parts_with_quotation_guess(text)

        if len(parts_cmd) > 0 and (parts_cmd[0] in self.shell.dict_cmds):
          sub_completer = self.shell.dict_cmds[parts_cmd[0]].sub_completer
          self.values = sub_completer.values(text)

        elif len(parts_cmd) > 0 and parts_cmd[0][0] == "!":
          sub_completer = SubCompleterLocalCommand()
          self.values = sub_completer.values(text)

        else:
          self.values = []

      if state < len(self.values):
        self.__log_debug(f"  --> return {self.values[state]}")
        return self.values[state].candidate
      else:
        return None

    except Exception as e:
      print(f"[complete]Exception = {e}")


class OneDriveShell:

  class ArgumentParserWithoutExit(argparse.ArgumentParser):
    """
      ArgumentParser without exiting on error.
    """

    def exit(self, status=0, message=None):
      lg.debug(
          f"Should exit with status '{status}' according to ArgumentParser original method.")

    def error(self, message):
      self.print_usage(sys.stderr)
      raise ValueError(message)

  # TODO Enhance help command with arguments for each command
  # TODO Add aliases possibility
  # TODO Keep previous history when relaunching the shell
  # TODO Remember configuration in a file
  # TODO Emphasize shell output by avoiding print command

  class Command(ABC):

    @beartype
    def __init__(
            self,
            name: str,
            my_argparser: argparse.ArgumentParser,
            sub_completer: SubCompleter):
      self.name = name
      self.argp = my_argparser
      self.sub_completer = sub_completer

    @beartype
    @abstractmethod
    def _do_action(self, args):  # Protected method
      pass

    def do_action(self, args):   # Public method
      self._do_action(args)

  @beartype
  def __init__(self, mgc: MsGraphClient):
    cinit()  # initialize colorama
    self.mgc = mgc
    self.root_folder = Oif.get_object_info(
        mgc, "/", no_warn_if_no_parent=True)[1]
    self.current_fi = self.root_folder
    self.only_folders = False
    self.ls_formatter = LsFormatter(MsFileFormatter(45), MsFolderFormatter(45))
    self.cp = Completer(self)
    self.initiate_commands()

  def initiate_commands(self):

    # Methods to buil commands
    def init_with_odshell(self2, name, my_argparser, sub_completer):
      super(self2.__class__, self2).__init__(name, my_argparser, sub_completer)

    def add_new_cmd(name, my_argparser, doa, sub_completer):
      new_class = type(f"Class_{name}", (OneDriveShell.Command, ), {
          "__init__": init_with_odshell,
          "_do_action": doa
      })
      self.dict_cmds[name] = new_class(name, my_argparser, sub_completer)

    # Actions of commands

    def action_cd(self2, args):
      self.change_to_path(args.path)

    def action_ll(self2, args):
      self.ls_formatter.print_folder_children(
          self.current_fi, start_number=1, only_folders=self.only_folders,
          with_pagination=args.p)

    def action_ls(self2, args):
      self.ls_formatter.print_folder_children_lite(
          self.current_fi, only_folders=self.only_folders,
          with_pagination=args.p)

    def action_lls(self2, args):
      self.ls_formatter.print_folder_children_lite_next(
          self.current_fi, only_folders=self.only_folders)

    def action_stat(self2, args):
      obj_name = args.remotepath
      if self.current_fi.relative_path_is_a_file(
              obj_name, force_children_retrieval=True):
        print(self.current_fi.get_child_file(obj_name).str_full_details())
      elif self.current_fi.relative_path_is_a_folder(obj_name):
        print(self.current_fi.get_child_folder(obj_name).str_full_details())
      else:
        print(f"{obj_name} is not a child of current folder({self.current_fi.path})")

    def action_get(self2, args):
      file_name = args.remotepath
      if self.current_fi.relative_path_is_a_file(file_name):
        self.mgc.download_file_content(
            self.current_fi.get_child_file(file_name).path, os.getcwd())
      else:
        print(f"{file_name} is not a file of current folder({self.current_fi.path})")

    def action_mv(self2, args):
      # lfip = last_folder_info_path
      # rt = remaining_text

      # Compute source path
      (lfip_src, rt_src) = MsObject.get_lastfolderinfo_path(
          self.root_folder, args.srcpath, self.current_fi)
      if lfip_src.relative_path_is_a_file(rt_src, True):
        src_obj = lfip_src.get_child_file(rt_src)
      elif lfip_src.relative_path_is_a_folder(rt_src, True):
        src_obj = lfip_src.get_child_folder(rt_src)
      else:
        print(f"'{args.srcpath}' is not a path of a remote object")
        return False

      # Compute dest path
      (lfip_dst, rt_dst) = MsObject.get_lastfolderinfo_path(
          self.root_folder, args.dstpath, self.current_fi)
      if lfip_dst.relative_path_is_a_folder(rt_dst, True):
        is_a_renaming = False
        dst_parent = lfip_dst.get_child_folder(rt_dst)
        dst_path2 = os.path.normpath(
            f"{dst_parent.path}/{rt_src}")
      elif lfip_dst.relative_path_is_a_file(rt_dst, True):
        return False
      else:
        is_a_renaming = True
        new_name = rt_dst
        dst_parent = lfip_dst
        dst_path2 = os.path.normpath(f"{lfip_dst.path}/{rt_dst}")

      lg.debug(f"move('{src_obj.path}','{dst_path2}')")

      r = self.mgc.move_object(src_obj.path, dst_path2)
      if not r:
        print(f"[Move]An error has occured")
        return False
      if is_a_renaming:
        src_obj.rename(new_name)
      src_obj.move_object(dst_parent)
      return True

    def action_rm(self2, args):
      (lfip_dst, rt_dst) = MsObject.get_lastfolderinfo_path(
          self.root_folder, args.dstpath, self.current_fi)
      if lfip_dst.relative_path_is_a_file(rt_dst, True):
        dst_obj = lfip_dst.get_child_file(rt_dst)
      elif lfip_dst.relative_path_is_a_folder(rt_dst, True):
        dst_obj = lfip_dst.get_child_folder(rt_dst)
      else:
        print(f"'{args.dstpath}' is not a path of a remote object")
        return False
      dst_path = os.path.normpath(f"{lfip_dst.path}/{rt_dst}")
      r = self.mgc.delete_file(dst_path)
      if r != 1:
        print("[rm]An error has occured")
        return False
      dst_obj.update_parent_before_removal()
      return True

    def action_pwd(self2, args):
      print(self.current_fi.path)

    def action_l_cd(self2, args):
      os.chdir(args.path)
      print(os.getcwd())

    # Arguments management
    myparser = OneDriveShell.ArgumentParserWithoutExit(
        prog='Onedrive Shell', usage='')

    # myparser.add_argument('num', type=int, help='num', nargs='?',default=None)
    sub_parser = myparser.add_subparsers(dest='cmd')
    sp_cd = sub_parser.add_parser('cd', help='Change directory')
    sp_cd.add_argument('path', type=str, help='Destination path')

    sp_ll = sub_parser.add_parser(
        'll', description='List current folder with details')
    sp_ll.add_argument(
        '-p',
        action='store_true',
        default=False,
        help='Enable pagination')
    sp_ls = sub_parser.add_parser(
        'ls', description='List current folder by column')
    sp_ls.add_argument(
        '-p',
        action='store_true',
        default=False,
        help='Enable pagination')
    sp_lls = sub_parser.add_parser(
        'lls', description='Continue listing folder in case of large folder')
    sp_lls = sub_parser.add_parser(
        'pwd', description='Print full path of current folder')
    sp_get = sub_parser.add_parser(
        'get', description='Download file in current folder')
    sp_get.add_argument('remotepath', type=str, help='remote file')
    sp_rm = sub_parser.add_parser(
        'rm', description='Remove a file or a folder')
    sp_rm.add_argument(
        'dstpath',
        type=str,
        help='File or Folder to be removed')
    sp_mv = sub_parser.add_parser(
        'mv', description='Move or rename a file or a folder')
    sp_mv.add_argument(
        'srcpath',
        type=str,
        help='Path of the remote file or folder')
    sp_mv.add_argument(
        'dstpath',
        type=str,
        help='Destination path of file or folder')
    sp_pwd = sub_parser.add_parser(
        'pwd', description='Print full path of the current folder')
    sp_stat = sub_parser.add_parser(
        'stat', description='Get info about object')
    sp_stat.add_argument('remotepath', type=str, help='destination object')
    sp_l_cd = sub_parser.add_parser('!cd', description="Change local folder")
    sp_l_cd.add_argument('path', type=str, help='Destination path')

    # (*) https://bugs.python.org/issue9334#msg169712

    self.__args_parser = myparser

    # Populate commands
    self.dict_cmds = {}
    add_new_cmd(
        'cd',
        sp_cd,
        action_cd,
        SubCompleterFileOrFolder(
            self,
            only_folder=True))
    add_new_cmd('ll', sp_ll, action_ll, SubCompleterNone())
    add_new_cmd('ls', sp_ls, action_ls, SubCompleterNone())
    add_new_cmd('lls', sp_lls, action_lls, SubCompleterNone())
    add_new_cmd(
        'stat',
        sp_stat,
        action_stat,
        SubCompleterFileOrFolder(
            self,
            only_folder=False))
    add_new_cmd(
        'get',
        sp_get,
        action_get,
        SubCompleterFileOrFolder(
            self,
            only_folder=False))
    add_new_cmd(
        'mv',
        sp_mv,
        action_mv,
        SubCompleterFileOrFolder(
            self,
            only_folder=False))
    add_new_cmd(
        'rm',
        sp_mv,
        action_rm,
        SubCompleterFileOrFolder(
            self,
            only_folder=False))
    add_new_cmd('pwd', sp_pwd, action_pwd, SubCompleterNone())
    # For any strange reason, cd does not work as common 'os.system'
    add_new_cmd('!cd', sp_l_cd, action_l_cd, SubCompleterLocalCommand())

  def change_max_column_size(self, nb):
    self.ls_formatter = LsFormatter(MsFileFormatter(nb), MsFolderFormatter(nb))

  def change_current_folder_to_parent(self):
    if self.current_fi.parent is not None:
      self.current_fi = self.current_fi.parent
    else:
      print("The current folder has no parent")

  def get_prompt(self):
    result = self.current_fi.name
    if self.current_fi.next_link_children is not None:
      result += "..."
    result += "> "
    return result

  def launch(self):

    readline.parse_and_bind('tab: complete')
    readline.set_completer(self.cp.complete)
    if sys.platform != "win32":
      readline.set_completion_display_matches_hook(self.cp.display_matches)
    # All line content will be managed by complemtion
    readline.set_completer_delims("")

    self.current_fi.retrieve_children_info(
        only_folders=self.only_folders, recursive=False)

    print(get_versionned_name())
    print('Type "help" or "license" for more information')
    while True:

      my_raw_input = input(f"{self.get_prompt()}")
      # Trim my_input and remove double spaces
      my_input = " ".join(my_raw_input.split())
      my_input = my_input.replace(" = ", "=")
      parts_cmd = shlex.split(my_input)
      if len(parts_cmd) > 0:
        cmd = parts_cmd[0]
      else:
        cmd = ""

      if cmd in ("q", "quit", "exit"):
        break

      if cmd == "":
        pass

      elif cmd in self.dict_cmds:
        args = []
        try:
          args = self.__args_parser.parse_args(parts_cmd)
          self.dict_cmds[cmd].do_action(args)
        except Exception as e:
          print(f"error: {e}")

      elif cmd.isdigit() and int(cmd) <= len(self.current_fi.children_folder):

        int_input = int(cmd)
        if int_input == 0:
          self.change_current_folder_to_parent()
        else:
          self.current_fi = self.current_fi.children_folder[int(my_input) - 1]

      elif cmd[0] == "!":
        os.system(my_raw_input[1:])

      elif cmd == "cd..":
        self.change_current_folder_to_parent()

      elif my_input == "set onlyfolders" or my_input == "set of":
        self.only_folders = True

      elif my_input == "set noonlyfolders" or my_input == "set noof":
        self.only_folders = False

      elif my_input[:7] == "set cs=" or my_input[:15] == "set columnsize=":
        str_cs = my_input[7:] if my_input[:7] == "set cs=" else my_input[15:]

        if not str_cs.isdigit():
          print("<value> of column size must be a digit")
        else:
          int_cs = int(str_cs)
          if (int_cs < 5) or (int_cs > 300):
            print("<value> must be a number between 5 and 300")
          else:
            self.change_max_column_size(int_cs)

      elif cmd == "help" or cmd == "h":
        if len(parts_cmd) == 1:
          print(get_versionned_name())
          print("")
          print("Available commands")
          for (k, v) in self.dict_cmds.items():
            print(f"  {k:20}{v.argp.description}")

          print(f"  {'<number>':20}Browse to folder <number>")
          print(f"  {'!<shell_command>':20}Launch local shell command")
          print(f"  {'set':20}Set a variable")
          print()
          print(f"  {'help/h':20}Print this help message")
          print(f"  {'license':20}Print license")
          print(f"  {'q/quit/exit':20}Quit the shell")
          print("")
          print(f"{PROGRAM_NAME} is also available as command line program.")
          print(f"Launch it with '-h' parameter for more information.")

        elif len(parts_cmd) == 2:
          if parts_cmd[1] in self.dict_cmds:
            self.dict_cmds[parts_cmd[1]].argp.print_help()
          elif parts_cmd[1] == "set":
            print("usage:")
            print("   set ( (<variable>|no<variable) | ( <variable>=<value> )")
            print()
            print("Variables that can be set and their aliases")
            print("    onlyfolders/of      boolean       Retrieve info about folders")
            print(
                "    columnsize/cs       int           Column Size of folder names and files names")
            print("                                      for long listing")

      elif cmd == "license":
        try:
          with open("LICENSE", "r") as f:
            l_content = f.read()
            print(l_content)
        except Exception:
          print(f"Error while reading license.")
          print(f"Please ensure that your copy of {PROGRAM_NAME} is complete.")

      else:
        print("unknown command")

  def full_path_from_root_folder(self, str_path):
    """
       Build full path of an object from string given in command line.
       If str_path starts with a separator, path from root_path is computed.
       Else path from current_folder is considered
    """
    if str_path[0] != '/':
      result = os.path.normpath(self.current_fi.path + '/' + str_path)[1:]
    else:
      result = os.path.normpath(str_path[1:])
    return result

  def change_to_path(self, folder_path):

    # Compute relative path from root_folder
    full_path = self.full_path_from_root_folder(folder_path)

    if self.root_folder.relative_path_is_a_folder(
            full_path, force_children_retrieval=True):
      self.current_fi = self.root_folder.get_child_folder(full_path)


class FormattedString():
  """
    Class to manage difference between String that is printed and String
    that is stored.
    Usefull when String are colorized or stylished because some specific
    non-printable characters are used.
  """

  def __init__(self, str_to_be_printed, str_raw, len_to_be_printed):
    self.to_be_printed = str_to_be_printed
    self.raw = str_raw
    self.len_to_be_printed = len_to_be_printed

  @staticmethod
  @beartype
  def build_from_string(what: str):
    return FormattedString(what, what, len(what))

  @staticmethod
  @beartype
  def build_from_colorized_string(what: str, raw_what: str):
    return FormattedString(what, raw_what, len(raw_what))

  @staticmethod
  def concat(*args):
    result = FormattedString("", "", 0)
    for s in args:
      if isinstance(s, str):
        result.to_be_printed += s
        result.raw += s
        result.len_to_be_printed += len(s)
      elif isinstance(s, FormattedString):
        result.to_be_printed += s.to_be_printed
        result.raw += s.to_be_printed
        result.len_to_be_printed += s.len_to_be_printed

    return result


class InfoFormatter(ABC):

  @abstractmethod
  def format(self, what):
    return "default"

  @abstractmethod
  def format_lite(self, what):
    return "default"

  @staticmethod
  @beartype
  def alignright(printable_what: FormattedString, nb: int, fillchar=" "):
    return FormattedString.build_from_colorized_string(
        f"{(fillchar * (nb - printable_what.len_to_be_printed))}{printable_what.to_be_printed}",
        f"{(fillchar * (nb - printable_what.len_to_be_printed))}{printable_what.raw}")

  @staticmethod
  @beartype
  def alignleft(printable_what: FormattedString, nb: int, fillchar=" "):
    return FormattedString.build_from_colorized_string(
        f"{printable_what.to_be_printed}{(fillchar * (nb - printable_what.len_to_be_printed))}",
        f"{printable_what.raw}{(fillchar * (nb - printable_what.len_to_be_printed))}")


class MsFolderFormatter(InfoFormatter):

  def __init__(self, max_name_size=25):
    self.max_name_size = max_name_size

  @beartype
  def format(self, what: MsFolderInfo):
    status_subfolders = "<subfolders ok>" if what.folders_retrieval_has_started() else ""
    status_subfiles = "<subfiles ok>" if what.files_retrieval_has_started() else ""
    fmdt = what.last_modified_datetime.strftime("%b %d %H:%M")

    if len(what.name) < self.max_name_size:
      fname = FormattedString.build_from_colorized_string(
          f"{Fore.BLUE}{Style.BRIGHT}{what.name}{Style.RESET_ALL}/",
          f"{what.name}/")
    else:
      fname = FormattedString.build_from_colorized_string(
          f"{Fore.BLUE}{Style.BRIGHT}{what.name[:self.max_name_size - 5]}{Style.RESET_ALL}.../",
          f"{what.name[:self.max_name_size - 5]}.../")

    result = FormattedString.concat(
        f"{what.size:>12}  {fmdt}  ",
        InfoFormatter.alignleft(
            fname,
            self.max_name_size),
        f"{what.child_count:>6}  {status_subfolders}{status_subfiles}")
    return result

  @beartype
  def format_lite(self, what: MsFolderInfo):
    return FormattedString.build_from_colorized_string(
        f"{Fore.BLUE}{Style.BRIGHT}{what.name}{Style.RESET_ALL}/",
        f"{what.name}/")


class MsFileFormatter(InfoFormatter):
  def __init__(self, max_name_size=25):
    self.max_name_size = max_name_size

  @beartype
  def format(self, what: MsFileInfo):
    fname = f"{what.name}" if len(
        what.name) < self.max_name_size else f"{what.name[:self.max_name_size - 5]}..."
    fmdt = what.last_modified_datetime.strftime("%b %d %H:%M")
    result = FormattedString.concat(
        f"{what.size:>12}  {fmdt}  ",
        InfoFormatter.alignleft(
            FormattedString.build_from_string(fname),
            self.max_name_size))
    return result

  @beartype
  def format_lite(self, what: MsFileInfo):
    return FormattedString.build_from_string(what.name)


class LsFormatter():

  # 'R' to keep colors - 'X' to keep the screen - 'F' no paging if one screen
  PAGER_COMMAND = 'less -R -X -F'

  @beartype
  def __init__(
          self,
          file_formatter: MsFileFormatter,
          folder_formatter: MsFolderFormatter,
          include_number: bool = True):
    self.file_formatter = file_formatter
    self.folder_formatter = folder_formatter
    self.column_printer = ColumnsPrinter(2)
    self.include_number = include_number

  @beartype
  def print_folder_children(
          self,
          fi: MsFolderInfo,
          start_number: int = 0,
          recursive: bool = False,
          only_folders: bool = True,
          depth: int = 999,
          with_pagination: bool = False):

    if ((not fi.folders_retrieval_has_started() and only_folders)
            or (not fi.files_retrieval_has_started() and not only_folders)):
      fi.retrieve_children_info(
          only_folders=only_folders,
          recursive=recursive,
          depth=depth)

    str_to_be_printed = ""
    i = start_number
    for c in fi.children_folder:
      prefix_number = f"{i:>3} " if self.include_number else ""
      str_to_be_printed += (
          f"{FormattedString.concat(prefix_number, self.folder_formatter.format(c)).to_be_printed.rstrip()}"
          "\n")

      i = i + 1
    if not only_folders:
      for c in fi.children_file:
        prefix_number = f"{i:>3} " if self.include_number else ""
        str_to_be_printed += (
            f"{FormattedString.concat(prefix_number, self.file_formatter.format(c)).to_be_printed.rstrip()}"
            "\n")
        i = i + 1
    str_to_be_printed = str_to_be_printed[:-1]  # remove last carriage return

    if with_pagination:
      pydoc.pipepager(str_to_be_printed, cmd=LsFormatter.PAGER_COMMAND)
    else:
      print(str_to_be_printed)

    # FIXME Recursive folder printing does not work (print_children does not
    # exist anymore)
    if recursive and depth > 0:
      for c in fi.children_folder:
        nb_children = c.print_children(
            start_number=i, recursive=False, depth=depth - 1)

        i += nb_children

    return i - start_number

  @beartype
  def print_folder_children_lite(
          self,
          fi: MsFolderInfo,
          only_folders: bool = True,
          with_pagination: bool = False):

    if ((not fi.folders_retrieval_has_started() and only_folders)
            or (not fi.files_retrieval_has_started() and not only_folders)):
      fi.retrieve_children_info(only_folders=only_folders)

    folder_names = map(
        lambda x: self.folder_formatter.format_lite(x),
        fi.children_folder)
    file_names = map(
        lambda x: self.file_formatter.format_lite(x),
        fi.children_file)
    all_names = list(folder_names) + list(file_names)
    self.column_printer.print_with_columns(all_names, with_pagination)

  @beartype
  def print_folder_children_lite_next(
          self, fi: MsFolderInfo, only_folders: bool = True):
    if ((not fi.folders_retrieval_is_completed() and only_folders)
            or (not fi.files_retrieval_is_completed() and not only_folders)):
      fi.retrieve_children_info_next(only_folders=only_folders)

    self.print_folder_children_lite(fi, only_folders)


class ColumnsPrinter():

  def __init__(self, sbc):
    self.sbc = sbc  # space between column

  def is_printable(self, max_len_line, elts, nb_columns):
    # elts = list of FormattedString
    nb_elts = len(elts)
    nb_lines = 1 + math.floor((len(elts) - 1) / nb_columns)

    column_sizes = [0] * nb_columns
    w = 0
    for i in range(0, nb_lines):
      elt = elts[i]
      c = 0
      if elt.len_to_be_printed > column_sizes[c]:
        column_sizes[c] = elt.len_to_be_printed
      w = column_sizes[0]

      for j in range(i + nb_lines, nb_elts, nb_lines):
        elt = elts[j]
        c += 1
        if elt.len_to_be_printed > column_sizes[c]:
          column_sizes[c] = elt.len_to_be_printed
        w += self.sbc + column_sizes[c]

      for d in range(c + 1, nb_columns):
        w += self.sbc + column_sizes[d]

      if w > max_len_line:
        return False

    return True

  def column_sizes(self, elts, nb_columns):
    # elts = list of FormattedString
    nb_elts = len(elts)
    nb_lines = 1 + math.floor((len(elts) - 1) / nb_columns)
    column_sizes = [0] * nb_columns
    for i in range(0, nb_lines):
      elt = elts[i]
      w = elt.len_to_be_printed
      c = 0
      if w > column_sizes[c]:
        column_sizes[c] = w

      for j in range(i + nb_lines, nb_elts, nb_lines):
        c += 1
        elt = elts[j]
        if elt.len_to_be_printed > column_sizes[c]:
          column_sizes[c] = elt.len_to_be_printed
        w += self.sbc + column_sizes[c]

    return column_sizes

  def nb_columns(self, elts):
    # elts = list of FormattedString
    low = 1
    high = 10
    while high - low > 1:
      mid = round((low + high) / 2)
      ans = self.is_printable(os.get_terminal_size().columns, elts, mid)
      if ans:
        low = mid
      else:
        high = mid
    if self.is_printable(os.get_terminal_size().columns, elts, high):
      return high
    else:
      return low

  def print_with_columns(self, what, with_pagination=False):
    # what : list of FormattedString to be printed
    if len(what) == 0:
      return
    nbc = self.nb_columns(what)
    cs = self.column_sizes(what, nbc)
    nb_lines = 1 + math.floor((len(what) - 1) / nbc)
    str_to_be_printed = ""
    for i in range(0, nb_lines):
      k = 0
      new_line = InfoFormatter.alignleft(what[i], cs[k])
      for j in range(i + nb_lines, len(what), nb_lines):
        k += 1
        new_line = FormattedString.concat(
            new_line,
            " " * self.sbc,
            InfoFormatter.alignleft(
                what[j],
                cs[k]))
      str_to_be_printed += new_line.to_be_printed.rstrip() + "\n"
    # remove trailing carriage return
    str_to_be_printed = str_to_be_printed[:-1]
    if with_pagination:
      pydoc.pipepager(str_to_be_printed, cmd=LsFormatter.PAGER_COMMAND)
    else:
      print(str_to_be_printed)
