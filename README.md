# OneDrive Client Program

ODC is a command line tool to interact with a Microsoft OneDrive Personal Storage.

![Python 3.10|3.11|3.12](https://img.shields.io/badge/python-3.10|3.11|3.12-blue)
![Tested with OneDrive Personal](https://img.shields.io/badge/Tested%20with-OneDrive%20Personal%20Account-blue)


## Available features

The following commands are available:

    init              Init connection
    put               Upload a file
    mput              Upload a complete folder
    whoami            Get information about connected user
    ls                List a folder content
    shell             Interactive shell
    get               Download a file
    mget              Download a complete folder
    stat              Get info from object
    share             Share a file or a folder
    mv                Move a file or a folder
    rm                Remove a file or a folder
    mkdir             Make a folder

`odc.py` with no argument launches the interactive shell. On linux platform, it includes a completion feature which recognizes remote files and folders.

`put`/`get` commands include the uploading/downloading of large file with a retry mechanism in case a chunk is not correctly uploaded/downloaded.

A progress bar is optionally available for downloading and uploading large file if the `tqdm` package is installed.

`mget` and `get` commands include a server throttling detection mechanism: if a throttling message is received, a timer is triggered until the server becomes available. In the case you plan to download large file or folder, it is recommended to install the `tqdm` package so that you can see the remaining time which may be significantly long (more than one hour).

Parameters of each command are described in help output

    $ odc.py <command> -h

## ODC in action

<img src="https://user-images.githubusercontent.com/7875007/211276237-f8e77085-e745-4ada-ba3e-e643393bfee9.gif" alt="ScreenCast ODC" width="100%">


The screencast above demonstrates the following features:
  - Uploading a complete folder
  - Browsing OneDrive from the shell
  - Autocompletion of folder and file names
  - Removing files from the shell
  - Detection of external changes by the shell
  - Uploading large file

## Requisites
A progress bar can be enabled when a large file or a complete folder is uploaded or downloaded. This feature requires the `tqdm` Python module.
Differential uploading and downloading (`mput` and `mget` commands) are available if a`quickxorhash` command is available in the `PATH` variable or if the `quickxorhash` Python module is installed.

## Installation

### On Azure portal

- Register an application with the following properties

      Supported account types      Personal Microsoft accounts only
      Platform                     Web
      Redirect URI                 https://localhost:8000/auth/redirect


- Create a secret assigned to this application

> Tip to register an application on Azure portal
> *Jul 7 2024 process*
> `portal.azure.com` ⇨ `Microsoft Entra ID` ⇨`App Registrations`


### On client computer

- Create Python environment and retrieve the code

      $ python3 -m venv envodc
      $ cd envodc
      $ git clone https://github.com/incognito1234/onedrive-client.git odc
      $ cd odc

- Prepare the Python environment and install the required packages

      $ . ../bin/activate
      $ pip install -r requirements.txt

- If you want to have a progress bar during upload or download, install `tqdm` package

      $ pip install tqdm

- On the Windows platform, import the package `pyreadline3`

      $ pip install pyreadline3

- Configure the connection to OneDrive

  - Copy `oauth_settings.yml.sample` to `oauth_settings.yml`
  - Copy/Paste `Application ID` and `Secret Value` of the Azure application into the relevant parts of `oauth_settings.yml` file
  - Initiate connection

      $ ./odc.py init
      ... Copy/Paste the provided URL into a browser
      ... Copy/Paste the URL from the browser into the console

- Optional: create a shortcut to launch ODC

      $ cat << EOF > /usr/local/sbin/odc
      #!/bin/sh

      <venv_folder>/bin/python <venv_folder>/odc/odc.py $@
      EOF

- It is now possible to use ODC

      $ cd <venv_folder>/odc
      $ ./odc.py <args>

  or if the shortcut has been created,

      $ odc <args>

## Changelog
_Only main changes are listed here_

### Version 1.4.1
- Fix a bug that could occur during the download process

### Version 1.4
- While listing folder, print year if last modification is older than 6 months
- Implements a workaround for the MSGraph bug affecting paths containing subfolders starting with v1.0 (see `CONTRIBUTING.MD`)

### Version 1.3
- Improves error management during download
- Add exclusion list as an option to the `mget` command
- Consider drive objects which are not file or folder (could be a Notebook)
- Use quickxorhash module if available (Thanks [wienand](https://github.com/incognito1234/onedrive-client/pull/5))
- Add `max_retrieved_children` to the `ls` command to list folders with more than 200 children

### Version 1.2
- Consider error when downloading file with re-try mechanisms
- Manage server throttling during download
- Add progress bar (with tqdm package) during downloading
- Add -l option for ls command

### Version 1.1
- Detect external changes when shell runs
- Shell enhancement: Add put command
- Shell enhancement: Add mkdir command
- Shell enhancement: Add recursive option to folder listing
- Shell enhancement: Allow multiple paths with ls command
- Various bug fixes

### Version 1.0
- Initial version


