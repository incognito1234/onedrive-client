#  Copyright 2019-2024 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
import logging

from requests_oauthlib import OAuth2Session
from lib.strpathutil import StrPathUtil
from pathlib import PurePosixPath
import json
import os
import pprint
import time

try:
  from tqdm import tqdm
except Exception:
  tqdm = None

lg = logging.getLogger("odc.msgraph")

class MsGraphException(Exception):

  def __init__(self, link):
    super().__init__("Exception from msgraph")
    self.src_link = link

  def __str__(self):
    return f"{self.args[0]} - raised with link '{self.src_link}'"


class MsGraphClient:

  # TODO Implement copy feature

  graph_url = 'https://graph.microsoft.com/v1.0'

  (TYPE_NONE, TYPE_FILE, TYPE_FOLDER) = (0, 1, 2)

  def __init__(self, mgc: OAuth2Session):
    self.mgc = mgc

  def get_user(self):
    # Send GET to /me
    user = self.mgc.get(f"{MsGraphClient.graph_url}/me")
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
        f"{MsGraphClient.graph_url}/me/events",
        params=query_params)
    # Return the JSON result
    return events.json()


  def get_ms_response_for_children_from_folder_path(
          self, folder_path):
    """ Get response value of ms graph for getting children info of a onedrive folder from folder path
    """

    # folder_path must start with '/'
    if folder_path == '':
      fp = f"{MsGraphClient.graph_url}/me/drive/items/root/children"
    else:
      fp = f"{MsGraphClient.graph_url}/me/drive/items/root:{folder_path}:/children"

    return self.get_ms_response_for_children_from_link(fp)

  def get_ms_response_for_children_from_id(
        self, id_item):
    """ Get response value of ms graph for getting children info of a onedrive folder from id
    """
    return self.get_ms_response_for_children_from_link(
      f"{MsGraphClient.graph_url}/me/drive/items/{id_item}/children"
    )


  def get_ms_response_for_children_from_link(
          self, link):
    """
     Get response value of ms graph for getting children info of a onedrive folder from a given link
     Bug of msGraph:
      Unable to get children of folder named v1.0
      A bug report has been opened https://feedbackportal.microsoft.com/feedback/idea/1c452009-cfd0-ef11-95f5-6045bdb154fd
      Discussion here:
        https://learn.microsoft.com/en-us/answers/questions/2145100/how-to-retrieve-children-of-onedrive-personal-fold
    """
    lg.debug(
        f"[get_ms_response_for_children_folder_path_from_link]Starting. link = "
        f"{link}"
        )

    ms_response = self.mgc.get(link)
    ms_response_json = ms_response.json()
    if 'error' in ms_response_json:
      lg.warn(
        f"[get_ms_response_for_children_folder_path_from_link]Error received. Return None"
        f" - response = {ms_response_json}"
        f" - link = {link}")
      raise MsGraphException(link)

    else:
      if "@odata.nextLink" in ms_response_json:
        next_link = ms_response_json["@odata.nextLink"]
      else:
        next_link = None

    return (ms_response_json['value'], next_link)

  def __tqdm_timer(self, sec: int, pos: int):
    t = tqdm(
        desc=f'Server is throttled - Wait {sec}s ',
        total=sec,
        bar_format='{desc}: {elapsed} ({percentage:2.0f}%)',
        position=pos,
        leave=False)
    st = time.time()
    for i in range(sec):
      time.sleep(1)
      t.update(1)


  def download_file_content_from_path(
          self,
          dst_path: str,
          local_dst: str,
          retry_if_throttled:bool =False, max_retry:int =5,
          list_tqdm: list = []):
    """
      Try to download file 'dst_path' in folder 'local_dst'
      If local_dst is a folder, the file will be downloaded with
      the same filename. Else, it will be the name of the downloaded file.

      Return 1 if download is successfull. 0 else.

    """
    file_name = dst_path.split("/").pop()
    if os.path.isdir(local_dst):
      local_fullpath = f"{local_dst}/{file_name}"
    else:
      local_fullpath = local_dst
    file_id = self.get_id_from_path(dst_path)
    return self.download_file_content_from_id_and_fullpath(
      file_id, local_fullpath, retry_if_throttled, max_retry, list_tqdm
    )


  def download_file_content_from_id_and_fullpath(
          self,
          file_id: str,
          local_fullpath: str,
          retry_if_throttled: bool=False, max_retry: int=5,
          list_tqdm: list = []):
    """
      Try to download file with id 'file_id' as full path 'local_full_path'
      'local_full_path' must include the destination filename

      Return 1 if download is sucessfull. 0 else.

    """
    # Inspired from https://gist.github.com/mvpotter/9088499
    file_name = str(PurePosixPath(local_fullpath).name)
    download_url = f"{MsGraphClient.graph_url}/me/drive/items/{file_id}/content"

    nb_retry = 0
    while True:
      nb_retry += 1
      nb_retry_exception = 0
      while True:

        try:
          r = self.mgc.get(download_url, stream=True)
          break
        except Exception as ex:
          nb_retry_exception += 1
          lg.error(
              f"Exception during download_file_content({dst_path}) - "
              f"{ex=} - {type(ex)=} - Wait 10 seconds"
          )
          if nb_retry_exception < 3:
            time.sleep(10)
          else:
            lg.info("A new exception occured and max retries (3) has been"
                    "reached. Exit function")
            return 0

      if r.ok:
        break

      # Manage Errors
      if (r.status_code not in (429, 503) or not retry_if_throttled):
        # 429 = TooManyRequests - 503 = Service Unavailable
        lg.error(
            f"Error during processing of download_file_content({dst_path}) - "
            f"{r.reason} (error {r.status_code})")
        return 0

      # From here status_code in (429, 503) and retry_if_throttled is True
      # https://learn.microsoft.com/en-US/sharepoint/dev/general-development/how-to-avoid-getting-throttled-or-blocked-in-sharepoint-online
      if nb_retry >= max_retry:
        lg.error(
            f"Error during processing of try_download_file_content({dst_path}) -"
            "Max retry has been reached. Stop function.")
        return 0

      header_params = {}
      for p in (
          "Retry-After",
              "RateLimit-Limit", "RateLimit-Remaining", "RateLimit-Reset"):
        header_params[p] = int(r.headers[p]) if p in r.headers else ""
      if header_params["Retry-After"] == "":
        header_params["Retry-After"] = 11

      lg.warn(
          f"Warn during processing of download_file_content({dst_path}) -"
          f"Client application has been throttled"
          f" (error code = {r.status_code}). Wait for "
          f"{header_params['Retry-After']} seconds - Retry nb = {nb_retry} "
          f" - RateLimit-Limit = {header_params['RateLimit-Limit']}"
          f" - RateLimit-Remaining = {header_params['RateLimit-Remaining']}"
          f" - RateLimit-Reset = {header_params['RateLimit-Reset']}"
          f" - Headers = {r.headers}")

      if tqdm is not None:
        self.__tqdm_timer(header_params["Retry-After"], len(list_tqdm))
      else:
        time.sleep(header_params["Retry-After"])

    # A tqdm will be initiated if content length is greater than 100 Mb
    if (
            tqdm is not None
            and 'Content-Length' in r.headers
            and int(r.headers['Content-Length']) > 100 * 1048576):
      n_tqdm = tqdm(
          desc=file_name,
          total=int(r.headers['Content-Length']),
          unit="B",
          unit_scale=True,
          unit_divisor=1024,
          colour="green" if len(list_tqdm) == 0 else "",
          position=len(list_tqdm),
          leave=len(list_tqdm) == 0)
      list_tqdm.append(n_tqdm)
    else:
      n_tqdm = None

    CHUNK_SIZE = 1048576 * 20  # 20 MB
    start = 0

    with open(local_fullpath, 'wb') as f:
      for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
        if chunk:  # filter out keep-alive new chunks
          lg.info(
              f"[download_file_content] Downloading {file_name} from {start}")
          f.write(chunk)
          f.flush()
          start = start + len(chunk)
          for t in list_tqdm:
            t.update(len(chunk))
    lg.info(
        f"[download_file_content] Download of file '{local_fullpath}' - OK")

    if n_tqdm is not None:
      list_tqdm.pop()
      n_tqdm.close()

    return 1

  def get_item_id_from_path(self, path):
    item_path = StrPathUtil.add_first_char_if_necessary(file_path, "/")


  def delete_file(self, file_path):
    file_path = StrPathUtil.add_first_char_if_necessary(file_path, "/")
    item_id = self.get_id_from_path(file_path)
    r = self.mgc.delete(
        f"{MsGraphClient.graph_url}/me/drive/items/{item_id}")
    if r.status_code == 404:
      return 0      # File not found
    elif r.status_code == 204:
      return 1      # OK
    else:
      return 2      # ??

  def raw_command(self, cmd):
    result = self.mgc.get(f"{MsGraphClient.graph_url}{cmd}")
    return result


  def put_file_content_from_fullpath_of_dstfolder(
          self,
          dst_folder_fullpath,
          src_file,
          dst_file_name=None,
          with_progress_bar=True):
    lg.info(f"Start put_file_content_from_fullpath_of_dstfolder('{dst_folder_fullpath}','{src_file}')")
    dst_folder = StrPathUtil.remove_first_char_if_necessary(dst_folder_fullpath, "/")
    parent_id = self.get_id_from_path(dst_folder_fullpath)
    if parent_id is None:
      lg.warn(f"[put_file_content_from_fullpath_of_dstfolder]parent_id not found for folder '{dst_folder_fullpath}'")
      return None
    return self.put_file_content_from_id_of_dstfolder(
      parent_id, src_file, dst_file_name, with_progress_bar
    )


  def put_file_content_from_id_of_dstfolder(
          self,
          dst_folder_id,
          src_file,
          dst_file_name=None,
          with_progress_bar=True):
    dst_file_name = dst_file_name if dst_file_name is not None else src_file.split("/").pop()

    total_size = os.path.getsize(src_file)
    lg.debug(f"File size = {total_size}")
    # For file size < 4Mb
    if total_size < (1048576 * 4):
      url = f"{MsGraphClient.graph_url}/me/drive/items/{dst_folder_id}:/{dst_file_name}:/content"
      headers = {
          # 'Content-Type' : 'text/plain'
          'Content-Type': 'application/octet-stream'
      }
      lg.debug(f"url put file = {url}")
      with open(src_file, 'rb') as f:
        r = self.mgc.put(
            url,
            data=f,
            headers=headers)

      return r

    else:
      # For file size > 4 Mb
      # https://docs.microsoft.com/fr-fr/graph/api/driveitem-createuploadsession?view=graph-rest-1.0
      url = f"{MsGraphClient.graph_url}/me/drive/items/{dst_folder_id}:/{file_name}:/createUploadSession"
      data = {
          "item": {
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
      lg.debug(f"total_size = {total_size:,}")

      # Init Progress bar
      if tqdm is not None and with_progress_bar:
        pbar = tqdm(
            desc=f"Uploading {dst_file_name}",
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024)
      else:
        pbar = None

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
              'Content-Length': str(current_size),
              'Content-Range': f"bytes {current_start}-{current_end}/{total_size}"}

          #simu_error = i==5
          if not simu_error:
            r = self.mgc.put(
                uurl,
                headers=headers,
                data=current_stream,
                withhold_token=True)
          status_code_put = r.status_code
          if ((status_code_put in (500, 502, 503, 504)) or (simu_error)):
            # 500 - Internal Server Error - 502: Bad Gateway - 503: Service
            # Unavailable - 504: Gateway Timeout

            r = self.mgc.get(uurl)
            lg.debug(
                f"Error with retry. Status of upload URL: {pprint.pformat(r.json())}")

            if not retry_status.max_retry_reach():
              retry_status.increase_retry()
              lg.warning(
                  "Error during uploading. Retry #{0}. Uploaded range: {1}->{2}. error code : {3}. Retrying upload".format(
                      retry_status.get_nb_retry(),
                      current_start,
                      current_end,
                      status_code_put))
              lg.info(f"Wait {retry_status.delay_wait()} seconds")
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
            if pbar is not None:
              pbar.update(current_size)
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
        lg.info(f"Correctly uploaded - id = {rjson['id']}")
        r = self.mgc.get(uurl)
        lg.debug(f"Status of upload URL: {pprint.pformat(r.json())}")

      # Close URL
      self.cancel_upload(uurl)

      lg.info(f"Session is finish - Stop_reason = {stop_reason}")
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
    dst_path = StrPathUtil.remove_first_char_if_necessary(dst_path, "/")
    parent_id = self.get_id_from_path(dst_path)
    dst_url = f"{MsGraphClient.graph_url}/me/drive/items/{parent_id}/children"
    data = {'name': new_folder, 'folder': {},
            '@microsoft.graph.conflictBehavior': 'rename'}
    data_json = json.dumps(data)
    r = self.mgc.post(
        dst_url,
        headers={
            'Content-Type': 'application/json'},
        data=data_json)

    if r.status_code == 201:
      result = r.json()
    else:
      result = None
      lg.error(
          "[create_folder]Error during creation of folder {0}/{1} - Error {2}".format(
              dst_path, new_folder, r.status_code))

    return result

  def path_type(self, path):
    """
      Return TYPE_FILE, TYPE_FOLDER, TYPE_NONE
    """
    r = self.get_ms_response_from_path(path)
    if r is None:
      return MsGraphClient.TYPE_NONE

    if ('folder' in r):
      return MsGraphClient.TYPE_FOLDER
    else:
      return MsGraphClient.TYPE_FILE


  def get_ms_response_from_path(self, object_path: str):
    """ Return ms_response if it is not an error.
        else return None
    """
    lg.debug(f"[get_ms_response_from_path]Get object with path '{object_path}'")
    object_path = StrPathUtil.remove_first_char_if_necessary(object_path, "/")

    if not self.__could_be_buggy_path(object_path):
      # Consider root
      prefixed_path = "" if object_path == "/" or object_path == "" else f":/{object_path}"
      r = self.mgc.get(
          f'{MsGraphClient.graph_url}/me/drive/items/root{prefixed_path}').json()
      lg.debug(f"[get_ms_response_from_path]return {r}")
      return None if 'error' in r else r

    else:
      lg.warn("[get_ms_response_from_path]Buggy path detected. Workaround applied")
      id_object = self.get_id_from_path(object_path)
      if id_object is not None:
        return self.get_ms_response_from_id(id_object)
      else:
        lg.warn("[get_ms_response_from_path]object not found")
        return None

  def get_ms_response_from_id(self, id_item: str):
    r = self.mgc.get(
        f'{MsGraphClient.graph_url}/me/drive/items/{id_item}').json()
    return r


  def get_id_from_path(self, object_path: str):
    """ Get ID of a msObject from path of these object.
        Return None if object is not found
    """
    object_path = StrPathUtil.remove_first_char_if_necessary(object_path, "/")

    posix_path = PurePosixPath(object_path)
    if not self.__could_be_buggy_path(object_path):
      prefixed_path = "" if object_path == "" else f":/{object_path}"
      r = self.mgc.get(
        f"{MsGraphClient.graph_url}/me/drive/root{prefixed_path}").json()
      return r["id"] if "id" in r else None
    else:
      return self.__get_id_from_buggy_path(object_path)


  def move_object(self, src_path: str, dst_path: str):
    lg.info(f"[move]Entering move_object ({src_path},{dst_path})")

    src_path = StrPathUtil.remove_first_char_if_necessary(src_path, '/')
    dst_path = StrPathUtil.remove_first_char_if_necessary(dst_path, '/')

    src_id = self.get_id_from_path(src_path)
    if src_id is None:
      lg.error(f"[move]Error during move. '{src_path}' not found.")
      return False

    type_dst = self.path_type(dst_path)

    posix_dst_path = PurePosixPath(dst_path)
    if type_dst == MsGraphClient.TYPE_FOLDER:
      lg.debug(f"[move]Destination is a folder")
      posix_src_path = PurePosixPath(src_path)
      id_parent = self.get_id_from_path(str(posix_dst_path))
      dst_name = str(posix_src_path.name)

    elif type_dst == MsGraphClient.TYPE_FILE:
      lg.error("[move]Destination file already exists")
      return False

    else:  # type_dst == MsGraphClient.TYPE_NONE
      lg.debug("[move]Destination does not exist.")
      posix_dst_path = PurePosixPath(dst_path)
      id_parent = self.get_id_from_path(str(posix_dst_path.parent))
      lg.debug(f"[move]id_parent = {id_parent}")
      dst_name = posix_dst_path.name

    if id_parent is None:
      lg.error("[move]parent not found")
      return False

    headers = {'Content-Type': 'application/json'}
    data = {
        "parentReference": {
            "id": id_parent
        },
        "name": dst_name
    }
    data_json = json.dumps(data)
    lg.debug(f"[move]Move from '{src_path}' to parent whose id is '{id_parent}'")
    r = self.mgc.patch(
      f"{MsGraphClient.graph_url}/me/drive/items/{src_id}",
      headers=headers, data=data_json)

    if r.status_code == 200:
      return True
    else:
      lg.error(f"[move]Error during move: {r.reason}")
      return False

  def create_share_link(self, path: str, share_type: str, password: str):
    share_path = StrPathUtil.remove_first_char_if_necessary(path, '/')

    itemId = self.get_id_from_path(share_path)
    if itemId is None:
      lg.error(f"[create_share_link]'{path}' does not exist")
      return None
    url = f"{MsGraphClient.graph_url}/me/drive/items/{itemId}/createLink"
    lg.debug(f"url = {url}")
    headers = {'Content-Type': 'application/json'}
    data = json.dumps({
        "type": share_type,
        "password": password,
        "scope": "anonymous"
    })
    r = self.mgc.post(url, headers=headers, data=data)
    if r.status_code in (
            200, 201):  # 200 = Already Exists - 201 = Just created
      r_json = r.json()
      if "link" in r_json and "webUrl" in r_json["link"]:
        return r_json["link"]["webUrl"]
      else:
        lg.error(
            f"[create_share_link]Error during link creation to '{path}' - webUrl not present in response")
    else:
      lg.error(
          f"[create_share_link]Error during link creation to '{path}' '{type}' - {r.reason}")
      return None

  def close(self):
    self.mgc.close()


  ### MSGRAPH_BUG MANAGEMENT
  def __could_be_buggy_path(self, path: str):
    """  `path` could be a buggy path
    """
    posix_path = PurePosixPath(path)
    return any(s.startswith('v1.0') or s.startswith("V1.0") for s in posix_path.parts)


  def __get_child_id_from_parent_id_and_child_name(self, parent_id: str, child_name: str):
    (ms_response, next_link) = self.get_ms_response_for_children_from_id(parent_id)
    while True:
      if ms_response is None:
        lg.warn(f"[__get_child_id_from_parent_id_and_child_name]Error while retrieving children of parent path for '{object_path}")
        return None
      for value_children in ms_response:
        if value_children['name'] == child_name:
          return value_children['id']
      if next_link is None:
        break
      (ms_response, next_link) = self.get_ms_response_for_children_from_link(next_link)
    return None


  def __get_id_from_buggy_path(self, path: str):
    posix_path = PurePosixPath(path)
    id_start = 1 if len(posix_path.parts) > 0 and posix_path.parts[0] == PurePosixPath("/") else 0
    parent_id = self.get_id_from_path("/")
    for part in posix_path.parts[id_start:]:
      str_part = str(part)
      parent_id = self.__get_child_id_from_parent_id_and_child_name(parent_id, str_part)
      if parent_id is None:
        break
    return parent_id

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
