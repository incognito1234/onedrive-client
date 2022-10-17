#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
import datetime
import pytz


def utc_dt_from_str_ms_datetime(str_ms_datetime):
  """ utc date_time from string representation of datetime from ms graph
  """
  try:
    result = datetime.datetime.strptime(str_ms_datetime, "%Y-%m-%dT%H:%M:%SZ")
  except ValueError:
    result = datetime.datetime.strptime(
        str_ms_datetime, "%Y-%m-%dT%H:%M:%S.%fZ")
  # datetime.datetime.now().strftime()
  return pytz.utc.localize(result)


def utc_dt_now():
  return datetime.datetime.now(pytz.utc)
