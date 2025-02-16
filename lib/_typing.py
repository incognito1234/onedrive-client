#  Copyright 2019-2025 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
from sys import version_info

if version_info >= (3, 9):
  List = list
  Tuple = tuple
  from beartype.typing import Optional
else:
  from typing import List, Tuple, Optional
