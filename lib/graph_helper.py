#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
import logging

from requests_oauthlib import OAuth2Session
import json
import os
import pprint
import time

lg = logging.getLogger("odc.msgraph")


class MsGraphClient:

  graph_url = 'https://graph.microsoft.com/v1.0'

  def __init__(self, mgc):
    self.mgc = mgc

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
    """ Get response value of ms graph for getting children info of a onedrive folder from folder path
    """

    # folder_path must start with '/'
    if folder_path == '':
      fp = '{0}/me/drive/root/children'.format(MsGraphClient.graph_url)
    else:
      fp = '{0}/me/drive/root:{1}:/children'.format(
          MsGraphClient.graph_url, folder_path)
    return self.get_ms_response_for_children_folder_path_from_link(
        fp, only_folder)

  def get_ms_response_for_children_folder_path_from_link(
          self, link, only_folder=False):
    """ Get response value of ms graph for getting children info of a onedrive folder from a given link
    """

    # folder_path must start with '/'
    if only_folder:
      param_urls = {
          '$filter': 'folder ne any',
          '$select': 'name,folder,id,size,parentReference,lastModifiedDateTime'}
    else:
      param_urls = ()

    ms_response = self.mgc.get(link, params=param_urls)

    if 'error' in ms_response:
      return None
    else:
      if "@odata.nextLink" in ms_response.json():
        next_link = ms_response.json()["@odata.nextLink"]
      else:
        next_link = None

    return (ms_response.json()['value'], next_link)

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
          lg.info(
              "[download_file_content] Downloading {0} from {1}".format(
                  dst_path, start))
          f.write(chunk)
          f.flush()
          start = start + CHUNK_SIZE
    lg.info(
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

    lg.info("Start put_file_content('{0}','{1}')".format(dst_folder, src_file))
    total_size = os.path.getsize(src_file)
    lg.debug("File size = {0}".format(total_size))
    file_name = src_file.split("/").pop()
    # For file size < 4Mb
    if total_size < (1048576 * 4):
      url = '{0}/me/drive/root:/{1}/{2}:/content'.format(
          MsGraphClient.graph_url,
          (dst_folder[1:] if dst_folder[0] == '/' else dst_folder),
          file_name
      )
      headers = {
          # 'Content-Type' : 'text/plain'
          'Content-Type': 'application/octet-stream'
      }
      lg.debug("url put file = {}".format(url))
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
      lg.debug("total_size = {0:,}".format(total_size))

      CHUNK_SIZE = 1048576 * 20  # 20 MB
      current_start = 0

      if total_size >= current_start + CHUNK_SIZE:
        current_end = current_start + CHUNK_SIZE - 1
      else:
        current_end = total_size - 1
      current_size = current_end - current_start + 1

      stop_reason = "OK"
      retry_status = self.RetryStatus(5)  # MaxRetry = 5

      simu_error = 0 == 1  # No simulation of error

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

          lg.debug(
              "{0} start/end/size/total/nbretry - {1:>15,}{2:>15,}{3:>15,}{4:>15,}{5:>6}".format(
                  i,
                  current_start,
                  current_end,
                  current_size,
                  total_size,
                  retry_status.get_nb_retry()))

          i = i + 1

          headers = {
              'Content-Length': "{0}".format(current_size),
              'Content-Range': "bytes {0}-{1}/{2}".format(current_start, current_end, total_size)
          }

          #simu_error = i==5
          if not simu_error:
            r = self.mgc.put(
                uurl,
                headers=headers,
                data=current_stream)
          status_code_put = r.status_code
          if ((status_code_put in (500, 502, 503, 504)) or (simu_error)):
            # 500 - Internal Server Error - 502: Bad Gateway - 503: Service
            # Unavailable - 504: Gateway Timeout

            r = self.mgc.get(uurl)
            lg.debug(
                "Error with retry. Status of upload URL: {0}".format(
                    pprint.pformat(
                        r.json())))

            if not retry_status.max_retry_reach():
              retry_status.increase_retry()
              lg.warning(
                  "Error during uploading. Retry #{0}. Uploaded range: {1}->{2}. error code : {3}. Retrying upload".format(
                      retry_status.get_nb_retry(),
                      current_start,
                      current_end,
                      status_code_put))
              lg.info("Wait {0} seconds".format(retry_status.delay_wait()))
              ner = r.json()['nextExpectedRanges'][0]
              current_start = int(ner[:ner.find('-')])
              if total_size >= current_start + CHUNK_SIZE:
                current_end = current_start + CHUNK_SIZE - 1
              else:
                current_end = total_size - 1
              current_size = current_end - current_start + 1
              time.sleep(retry_status.delay_wait())
              fin.seek(current_start)
            else:
              raise Exception("Maximum retry reached after an error")

          elif status_code_put == 404:  # Not found. Upload session no longer exists
            lg.error(
                "Upload session no longer exists (error code 404). Stop upload")
            raise Exception(
                "Upload session no longer exists. Please relaunch upload. Current range: {0}->{1}.".format(
                    current_start, current_end))

          elif status_code_put not in (202, 201, 200):  # Accepted/Created/OK
            msg_error = "Error during uploading. uploaded range: {0}->{1}. status_code : {2}. Stop upload".format(
                current_start, current_end, r.status_code)
            lg.error(msg_error)

            raise Exception(msg_error)
            # r is a object with type 'request.response' which is not serializable as json - an error is raised
            # 'TypeError: Object of type 'Response' is not JSON serializable'
            # lg.error("Error during uploading. uploaded range: {0}->{1}. status_code : {2}. response : {3}".format(
            #  current_start, current_end, r.status_code, pprint.pformat(json.dumps(r))
            # ))

          else:  # status_code_put in (202, 201, 200)
            current_start = current_end + 1
            if total_size >= current_start + CHUNK_SIZE:
              current_end = current_start + CHUNK_SIZE - 1
            else:
              current_end = total_size - 1
            current_size = current_end - current_start + 1

            if retry_status.get_nb_retry() > 0:
              retry_status.reset()

      rjson = r.json()
      if "id" not in rjson:
        lg.error("Error during uploading")
      else:
        lg.info("Correctly uploaded - id = {0}".format(rjson["id"]))
        r = self.mgc.get(uurl)
        lg.debug("Status of upload URL: {0}".format(pprint.pformat(r.json())))

      # Close URL
      self.cancel_upload(uurl)

      lg.info("Session is finish - Stop_reason = {0}".format(stop_reason))
      r = r1
      return r

  def cancel_upload(self, upload_url):
    r = self.mgc.delete(upload_url)

    return r

  def create_folder(self, dst_path, new_folder):
    """
      If successfull, return the name of the new folder.
      Else return none
    """
    if (dst_path == '/') | (dst_path == ''):
      dst_url = '{0}/me/drive/root:/children'.format(MsGraphClient.graph_url)
    else:
      # Remove first '/' if necessary
      dst_path2 = dst_path[1:] if dst_path[0] == '/' else dst_path
      dst_url = '{0}/me/drive/root:/{1}:/children'.format(
          MsGraphClient.graph_url, dst_path2)

    data = {'name': new_folder, 'folder': {},
            '@microsoft.graph.conflictBehavior': 'rename'}
    data_json = json.dumps(data)
    r = self.mgc.post(
        dst_url,
        headers={
            'Content-Type': 'application/json'},
        data=data_json)

    if r.status_code == 201:
      r_json = r.json()
      result = r_json["name"]
    else:
      result = None
      lg.error(
          "[create_folder]Error during creation of folder {0}/{1} - Error {2}".format(
              dst_path, new_folder, r.status_code))

    return result

  class RetryStatus:

    def __init__(self, max_retry=5):
      self.__nb_retry = 0
      self.max_retry = max_retry
      self.__delay = 15  # second

    def reset(self):
      self.__nb_retry = 0
      self.__delay = 15

    def increase_retry(self):
      if self.max_retry_reach():
        return False
      self.__nb_retry += 1
      self.__delay *= 2
      return True

    def get_nb_retry(self):
      return self.__nb_retry

    def max_retry_reach(self):
      return self.__nb_retry >= self.max_retry

    def delay_wait(self):
      return self.__delay
