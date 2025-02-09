## Introduction
This document is intended for contributors and developers who are working on the OneDrive Client Program. It provides details about a known bug in MSGraph that affects certain commands when using specific paths. The information here is meant to help understand the issue and the implemented workaround.

## How to Contribute
If you have encountered this issue or have suggestions for a better workaround, please contribute by:
- Opening an issue on the GitHub repository.
- Participating in the discussion linked in the section 'Discussion with the MS community MS support'
- Submitting a pull request with potential fixes or improvements.


## Note about what seems to be a bug in MSGraph
It seems that MsGraph has been behaving buggy for a while. This issue appears for some commands that apply to a drive item and take the `item-path` as a parameter. If the `item-id` is used, the API behaves as expected. After multiple tests, it appears that the bug only occurs for full paths containing a subfolder starting with `v1.0`, or if a non-final subfolder is `V1.0`.

### Examples of buggy and not buggy paths
Here are some examples of buggy and not buggy paths:
| Path                   | Generates a 404 error | What seems to be the bug reason           |
| ---------------------- | --------------------- | ----------------------------------------- |
| `Test/v1.0`            | Yes                   | ends with `v1.0`                          |
| `Test/V1.0`            | No                    | N/A                                       |
| `Test/v1.0/subfolder`  | Yes                   | includes a subfolder starting with `v1.0` |
| `Test/v1.0a/subfolder` | Yes                   | includes a subfolder starting with `v1.0` |
| `Test/V1.0/subfolder`  | Yes                   | includes a subfolder named `V1.0`         |
| `Test/V1.0a/subfolder` | No                    | N/A                                       |

### Affected commands
Tests shows that the following commands seems to be affected:

| Command                                       | Documentation                                                                                             | HTTP request                                             |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| Get driveItem                                 | [here](https://learn.microsoft.com/en-us/graph/api/driveitem-get?view=graph-rest-1.0&tabs=http)           | `GET /me/drive/root:/{item-path}`                        |
| List children of a driveItem                  | [here](https://learn.microsoft.com/en-us/graph/api/driveitem-list-children?view=graph-rest-1.0&tabs=http) | `GET /me/drive/root:/{item-path}:/children`              |
| Create a new folder in a drive                | [here](https://learn.microsoft.com/en-us/graph/api/driveitem-post-children?view=graph-rest-1.0&tabs=http) | `POST /me/drive/root:/{item-path}:/children`             |
| Move a DriveItem to a new folder              | [here](https://learn.microsoft.com/en-us/graph/api/driveitem-move?view=graph-rest-1.0&tabs=http)          | `PATCH /me/drive/root:/{item-path}:`                     |
| Upload or replace the contents of a driveItem | [here](https://learn.microsoft.com/en-us/graph/api/driveitem-put-content?view=graph-rest-1.0&tabs=http)   | `PUT /me/drive/root:/{parent-path}:/{filename}:/content` |

Please note that many combinations of command/buggy path/not buggy path have been tested, but it is not guaranteed that all of them have been covered.


### Discussion with the MS community MS support
A discussion about this subject is available [here](https://learn.microsoft.com/en-us/answers/questions/2145100/how-to-retrieve-children-of-onedrive-personal-fold)


This bug does not seem to affect business accounts and could not be reproducted by the MS support. Feel free to comment it if you encountered this issue on your side. It will be very helpfull.


While waiting for a potential resolution, a workaround has been implemented.