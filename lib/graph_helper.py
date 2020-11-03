from requests_oauthlib import OAuth2Session
from lib.shell_helper import MsFolderInfo, MsFileInfo, MsObject
from lib.log import Logger
import json
import os
import pprint


class MsGraphClient:

  graph_url = 'https://graph.microsoft.com/v1.0'

  def __init__(self, mgc, logger):
    self.mgc = mgc
    self.logger = logger

  def set_logger(self, logger):
    self.logger = logger

  def get_user(self):
    # Send GET to /me
    user = self.mgc.get('{0}/me'.format(MsGraphClient.graph_url))
    # Return the JSON result
    return user.json()

  def get_calendar_events(self):
    # Configure query parameters to
    # modify the results
    query_params = {
        '$select': 'subject,organizer,start,end',
        '$orderby': 'createdDateTime DESC'
    }

    # Send GET to /me/events
    events = self.mgc.get(
        '{0}/me/events'.format(MsGraphClient.graph_url), params=query_params)
    # Return the JSON result
    return events.json()

  def get_ms_response_for_children_folder_path(
          self, folder_path, only_folder=False):
    """ Get response value of ms graph for getting children info of a onedrive folder
    """

    if folder_path == '':
      fp = '{0}/me/drive/root/children'.format(MsGraphClient.graph_url)
    else:
      fp = '{0}/me/drive/root:/{1}:/children'.format(
          MsGraphClient.graph_url, folder_path)

    if only_folder:
      param_urls = {
          '$filter': 'folder ne any',
          '$select': 'name,folder,id,size'}
    else:
      param_urls = ()
    ms_response = self.mgc.get(fp, params=param_urls)

    if 'error' in ms_response:
      return None
    else:
      if "@odata.nextLink" in ms_response.json():
        next_link = ms_response.json()["@odata.nextLink"]
      else:
        next_link = None

      return ms_response.json()['value']

  def download_file_content(self, dst_path, local_dst):
    # Inspired from https://gist.github.com/mvpotter/9088499

    r = self.mgc.get('{0}/me/drive/root:/{1}:/content'.format(
        MsGraphClient.graph_url, dst_path
    ), stream=True)

    if os.path.isdir(local_dst):
      file_name = dst_path.split("/").pop()
      local_filepath = "{0}/{1}".format(local_dst, file_name)
    else:
      local_filepath = local_dst

    CHUNK_SIZE = 1048576 * 20  # 20 MB
    start = 0
    with open(local_filepath, 'wb') as f:
      for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
        if chunk:  # filter out keep-alive new chunks
          self.logger.log_info(
              "[download_file_content] Downloading {0} from {1}".format(
                  dst_path, start))
          f.write(chunk)
          f.flush()
          start = start + CHUNK_SIZE
    self.logger.log_info(
        "[download_file_content] Download of file '{0}' to '{1}' - OK".format(dst_path, local_dst))

    return 1

  def delete_file(self, file_path):
    r = self.mgc.delete('{0}/me/drive/root:/{1}:'.format(
        MsGraphClient.graph_url, file_path
    ))
    if r.status_code == 404:
      return 0      # File not found
    elif r.status_code == 204:
      return 1      # OK
    else:
      return 2      # ??

  def raw_command(self, cmd):
    result = self.mgc.get("{0}{1}".format(
        MsGraphClient.graph_url, cmd
    ))
    return result

  def put_file_content(self, dst_folder, src_file):

    self.logger.log_debug(
        "Start put_file_content('{0}','{1}')".format(
            dst_folder, src_file))
    total_size = os.path.getsize(src_file)
    self.logger.log_debug("File size = {0}".format(total_size))
    file_name = src_file.split("/").pop()
    # For file size < 4Mb
    if total_size < (1048576 * 4):
      url = '{0}/me/drive/root:/{1}/{2}:/content'.format(
          MsGraphClient.graph_url,
          dst_folder,
          file_name
      )
      headers = {
          # 'Content-Type' : 'text/plain'
          'Content-Type': 'application/octet-stream'
      }
      self.logger.log_debug("url put file = {}".format(url))
      r = self.mgc.put(
          url,
          data=open(src_file, 'rb'),
          headers=headers)

      return r

    else:
      # For file size > 4 Mb
      # https://docs.microsoft.com/fr-fr/graph/api/driveitem-createuploadsession?view=graph-rest-1.0
      url = '{0}/me/drive/root:/{1}/{2}:/createUploadSession'.format(
          MsGraphClient.graph_url,
          dst_folder,
          file_name
      )
      data = {
          "item": {
              "@odata.type": "microsoft.graph.driveItemUploadableProperties",
              "@microsoft.graph.conflictBehavior": "replace"
          }
      }

      # Initiate upload session
      data_json = json.dumps(data)
      r1 = self.mgc.post(
          url,
          headers={
              'Content-Type': 'application/json'
          },
          data=data_json
      )
      r1_json = r1.json()
      uurl = r1_json["uploadUrl"]

      # Upload parts of file
      total_size = os.path.getsize(src_file)
      self.logger.log_debug("total_size = {0:,}".format(total_size))

      CHUNK_SIZE = 1048576 * 20  # 20 MB
      current_start = 0

      if total_size >= current_start + CHUNK_SIZE:
        current_end = current_start + CHUNK_SIZE - 1
      else:
        current_end = total_size - 1
      current_size = current_end - current_start + 1

      stop_reason = "OK"
      with open(src_file, 'rb') as fin:
        i = 0
        while True:
          current_stream = fin.read(current_size)

          if not current_stream:
            stop_reason = "end_of_stream"
            break
          if current_start > total_size:
            stop_reason = "current_size_oversized"
            break
          if i > 2000:
            stop_reason = "exceed_number_of_loop"
            break

          self.logger.log_debug(
              "{0} start/end/size/total - {1:>15,}{2:>15,}{3:>15,}{4:>15,}".format(
                  i, current_start, current_end, current_size, total_size))

          i = i + 1

          headers = {
              'Content-Length': "{0}".format(current_size),
              'Content-Range': "bytes {0}-{1}/{2}".format(current_start, current_end, total_size)
          }

          current_start = current_end + 1
          if total_size >= current_start + CHUNK_SIZE:
            current_end = current_start + CHUNK_SIZE - 1
          else:
            current_end = total_size - 1
          current_size = current_end - current_start + 1

          r = self.mgc.put(
              uurl,
              headers=headers,
              data=current_stream)

      # Close URL
      self.cancel_upload(uurl)

      self.logger.log_info(
          "Session is finish - Stop_reason = {0}".format(stop_reason))
      r = r1
      return r

  def cancel_upload(self, upload_url):
    r = self.mgc.delete(upload_url)

    return r

  def get_object_info(self, dst_path):
    r = self.mgc.get('{0}/me/drive/root:/{1}'.format(
        MsGraphClient.graph_url, dst_path
    )).json()
    if 'error' in r:
      return (r['error']['code'], None)
    mso = MsObject.MsObjectFromMgcResponse(self, r)
    return (None, mso)
