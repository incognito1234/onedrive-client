#  Copyright 2019-2022 Jareth Lomson <jareth.lomson@gmail.com>
#  This file is part of OneDrive Client Program which is released under MIT License
#  See file LICENSE for full license details
from lib.graph_helper import MsGraphClient
import lib.shell_helper
from lib.datetime_helper import str_from_ms_datetime


class ObjectInfoFactory:

  @staticmethod
  def get_object_info(mgc, dst_path):
    r = mgc.mgc.get('{0}/me/drive/root:/{1}'.format(
        MsGraphClient.graph_url, dst_path
    )).json()
    if 'error' in r:
      return (r['error']['code'], None)

    if ('folder' in r):
      # import pprint
      # pprint.pprint(mgc_response_json)
      mso = ObjectInfoFactory.MsFolderFromMgcResponse(mgc, r)
    else:
      mso = ObjectInfoFactory.MsFileInfoFromMgcResponse(mgc, r)
    return (None, mso)

  @staticmethod
  def MsFolderFromMgcResponse(mgc, mgc_response_json, parent=None):

    # Workaround following what seems to be a bug. Space is replaced by "%20" sequence
    #   in mgc_response when parent name contains a space
    if parent is not None:
      parent_path = parent.get_full_path()
    else:
      parent_path = mgc_response_json['parentReference']['path'][12:]

    return lib.shell_helper.MsFolderInfo(
        full_path="{0}/{1}".format(
            parent_path,
            mgc_response_json['name']),
        name=mgc_response_json['name'],
        mgc=mgc,
        id=mgc_response_json['id'],
        child_count=mgc_response_json['folder']['childCount'],
        size=mgc_response_json['size'],
        parent=parent,
        lmdt=str_from_ms_datetime(mgc_response_json['lastModifiedDateTime'])
    )

  @staticmethod
  def MsFileInfoFromMgcResponse(mgc, mgc_response_json):
    if 'quickXorHash' in mgc_response_json['file']['hashes']:
      qxh = mgc_response_json['file']['hashes']['quickXorHash']
    else:
      qxh = None
    return lib.shell_helper.MsFileInfo(mgc_response_json['name'],
                                         mgc_response_json['parentReference']['path'][13:],
                                         mgc,
                                         mgc_response_json['id'],
                                         mgc_response_json['size'],
                                         qxh,
                                         mgc_response_json['file']['hashes']['sha1Hash'],
                                         str_from_ms_datetime(mgc_response_json['createdDateTime']),
                                         str_from_ms_datetime(mgc_response_json['lastModifiedDateTime'])
                                         )
