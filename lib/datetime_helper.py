import datetime
import pytz


def str_from_ms_datetime(str_ms_datetime):
  """ localized date_time from string representation of datetime from ms graph
  """
  try:
    result = datetime.datetime.strptime(str_ms_datetime, "%Y-%m-%dT%H:%M:%SZ")
  except ValueError:
    result = datetime.datetime.strptime(
        str_ms_datetime, "%Y-%m-%dT%H:%M:%S.%fZ")
  return pytz.utc.localize(result)
