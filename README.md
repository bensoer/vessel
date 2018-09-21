# Vessel
Vessel is an automation/orchestration tool designed for Windows infrastructure

Vessel is implemented to run as Windows Services and primarily functions as a script aggregating system. Users
develop scripts in a supported language and then vessel will distribute and run it on the desired nodes based on
HTTP or Terminal (coming soon) requests.

## Prerequisites
Vessel is written in Python and thus required Python 3.6+ in order to run. In addition to this, in order to use the
Windows Services API, you will also need to install `pywin32`. A tutorial on how to install Python 3.6 with pywin32
on Windows 7 or 10 can be found here: https://blog.bensoer.com/create-windows-service-in-python-3/

## Setup

To setup vessel you need to start by setting up the master node.
1) Download or clone this repo contents
2) Copy to `C:\vessel` in your system
3) In `C:\vessel\config\services.init.template` rename the file to `services.init` and verify/fillout the config with
the correct information. Make sure to change the `private_key_password`!
4) Open command as an administrator and cd to `C:\vessel`
5) Install the master node service by entering `python master.py install`
6) Start the master node service by entering `python master.py start`

Once this has started you can then install vessel nodes on other systems.
1) Download or clone the repo contents onto a node
2) Repeat the above steps until step 4
3) To install the node service, enter the following into a command with administrator priveleges `python node.py install`
4) Start the node service by entering `python node.py start`

The node will then automatically connect to the master node after generating its required keys

## Currently Supported Script Files
The following are filetypes and their associated engines they are executed with. Vessel will automatically use the 
appropriate engine when it detects the filetype of the requested file. A script that does not match a supported filetype
will not be included as an available script to execute on Vessel.

* Python3 (.py)
* Powershell (.ps1)
* Batch (.bat)
* NodeJS (.js)

## Node Configuration For Scripts
To run certain scripts on nodes, the end host system will need to have certain settings configured. Eventually
these should be taken care of as part of the nodes startup phase.

For powershell, open Powershell as an Administrator and run the following command:
```ps1
Set-ExecutionPolicy RemoteSigned
```
This will allow the node to execute powershell scripts

For python, the python executable must be set in the system PATH. You can test this by opening a command and then
typing
```bash
%PATH%
```
This will allow the node to execute python scripts. This is likely already setup as it is required in order to install
the node or master services.

For NodeJS, the node executable must be set in the system PATH. You can test this by opening a command then then typing
```bash
%PATH%
```
Vessel will fail to execute your NodeJS scripts if the `node` executable cannot be found within the PATH. Additionally,
Vessel will not handle any package management or dependency calls prior to executing. The script executed by vessel should
handle this automatically.


## Security
Obviously, communication between nodes and masters will likely contain sensitive data. To securely transfer data
between points, RSA and AES are both used - RSA to transfer the AES key from the node to the master, and then AES from
then onwards. Each node generates its own AES key. On successful connection to the master, the master node sends its
public RSA key. The node then uses this to encrypt its AES key and send it to the master. The master then decrypts this
and further communication continues with the AES key.

In order to avoid issues with data in transit, all data is also Base64 encoded before sent over the internet to avoid
read and write issues on the end systems.

## Vessel Internal Command Codes:
The following are command codes used for communication between processes and nodes. It is a CRUD-like system that
abstracts communication internally from outside interactions. This allows for commands passed in by HTTP or Terminal
or internally to be able to translate and communicate the same and then translate back to their desired format
(HTTP as JSON, Terminal as text, etc). The purpose is to document the commands for consistency within the
application and to help developers pickup on application structure

GET - For fetching information from nodes
- SCRIPTS - Fetch scripts on a node. The data is fetched from the database on the node
- PING - Fetch general node information and meta
- DEPLOYMENTS - Fetch deployment information

EXEC - For executing on nodes
- SCAN.SCRIPTS - Rescan the file system for scripts data. Works same as GET SCRIPTS except reads from the file-system
and updates the database afterwards
- DEPLOYMENTS.EXECUTE - Executes a deployment which is a group of scripts in a specific order
- SCRIPTS.EXECUTE - Executes a script
- FAILED.NOTFOUND - Vessel system processed everything fine. However the request script was not found on the executing node
- FAILED - Vessel system processed everything fine. However the script executed error'd or failed to execute
- SUCCESS - Vessel system processed everything fine. Script executed ran successfully

MIG - Migrates scripts from master to node and vise-versa

CREATE - For creating resources
- DEPLOYMENT - Creates a deployment record

SYS - For internal communication passing between processes and nodes
- RESTART - Sent from Master to Node to make node disconnect and start reconnect cycles
- CONN.CLOSE - Sent from Node to Master to tell Master node is gracefully closing and to terminate the connection on its side
- SHUTDOWN - Sent to main thread to stop process and start shutdown

ERROR - For errors with the Vessel system and its execution

## Resources
Install Python Non-Interactively:
https://www.python.org/download/releases/2.5/msi/

