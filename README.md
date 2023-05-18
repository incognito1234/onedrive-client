# OneDrive Client Program

ODC is a command line tool to interact with a Microsoft OneDrive Personal Storage.

## Available features

The following commands are available:

    init              Init connexion
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

`python odc.py` with no arguments launch the interactive shell. On linux platform, it includes a completion feature which recognizes remote files and folders.

`put` command includes the uploading of large file with a retry mechanism in case a chunk is not correctly uploaded.

Parameters are described in help output

    $ python odc.py <command> -h

## ODC in action

<img src="https://user-images.githubusercontent.com/7875007/211276237-f8e77085-e745-4ada-ba3e-e643393bfee9.gif" alt="ScreenCast ODC" width="80%">


The screencast above demonstrates the following features:
  - Uploading of complete folder
  - Browsing OneDrive from the shell
  - Autocompletion of folder and file name
  - File removal from the shell
  - Detection of external changes by shell
  - Large file upload

## Requisites
ODC has been tested with the following environment
- python 3.8/python 3.9/python 3.10
- Personal Microsoft account

Progress bar can be enabled when a large file is uploaded. This features needs `tqdm` python module.
Differential uploading and downloading (`mput` and `mget` comands) are available if a`quickxorhash` command is available in `PATH` variable)

## Installation

### On Azure portal

- Register an application with the following properties

      Supported account types      Personal Microsoft accounts only
      Redirect URI                 https://localhost:8000/auth/redirect


- Create a secret assigned to this application

> Tip to register an application on azure portal
> *Oct 2022 process*
> `portal.azure.com` ⇨ `Azure Active Directory` ⇨`App Registration`


### On client computer

- Create python environment and retrieve the code

      $ python3 -m venv envodc
      $ cd envodc
      $ git clone https://github.com/incognito1234/onedrive-client.git odc
      $ cd odc

- Prepare python environment and install required packages

      $ . ../bin/activate
      $ pip -r requirements.txt

- On Windows platform, import the package pyreadline3

      $ pip install pyreadline3

- Configure connexion to OneDrive

  - Copy `oauth_settings.yml.sample` in `oauth_settings.yml`
  - Copy/Paste `Application ID` and `Secret Value` of azure application in the relevant parts of `oauth_settings.yml` file
  - Initiate connexion

        $ python odc.py init
        ... Copy/Paste provided URL in a browser
        ... Copy/Paste URL of the browser in the console

- Optional: create a shortcut to launch ODC

        $ cat << EOF > /usr/local/sbin/odc
        #!/bin/sh

        <venv_folder>/bin/python <venv_folder>/odc/odc.py
        EOF

- It is now possible to use ODC

      $ cd <venv_folder>/odc
      $ python odc.py <args>

  or if you have created the shortcut

      $ odc <args>

## Changelog
_Only main changes are listed here_

### Version 1.1
- Detect external changes when shell runs
- Shell enhancement: Add put command
- Shell enhancement: Add mkdir command
- Shell enhancement: Add recursive option to folder listing
- Shell enhancement: Allow multiple paths with ls command
- Various bug fixes

### Version 1.0
- Initial version


