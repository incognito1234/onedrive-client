# OneDrive Client Program

ODC is a tool to interact with a Microsoft OneDrive Personal Storage.

## Available features

    init              Init connexion
    put               Upload a file
    mput              Upload a complete folder
    whoami            Get information about connected user
    ls                List a folder content
    shell             Interaction shell
    get               Download a file
    mget              Download a complete folder
    stat              Get info from object
    share             Share a file or a folder
    mv                Move a file or a folder
    rm                Remove a file or a folder
    mkdir             Make a folder

Parameters are described in help output

    python odc.py <command> -h

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

- Configure connexion to OneDrive

  - Copy `oauth_settings.yml.sample` in `oauth_settings.yml`
  - Copy/Paste `Application ID` and `Secret Value` of azure application in the relevant parts of `oauth_settings.yml` file
  - Initiate connexion

        $ python odc.py init
        ... and follow instructions



