import uuid
import subprocess
from subprocess import CalledProcessError
import json
from db.models.Script import Script
from db.models.Deployment import Deployment
from db.models.DeploymentScript import DeploymentScript
import os
import platform
try:
    from pip._internal.utils.misc import get_installed_distributions
except ImportError:  # pip<10
    from pip import get_installed_distributions
import base64
import utils.enginemaps as enginemaps

# THIS IS THE APP WIDE GLOBAL
vessel_version = "1.0.0"

def migrate(root_dir, sql_manager, request, logger):

    node_guid, serialized_script = request['params']
    script = Script.fromDictionary(serialized_script)
    script.file_path = root_dir + os.sep + "scripts"  # set the path to the new dir location
    script.id = sql_manager.insertScriptIfNotExists(script).id

    file_path = root_dir + os.sep + "scripts" + os.sep + script.file_name
    fp = open(file_path, 'wb+')
    file_data = request['rawdata']
    encoded_data = base64.b64decode(file_data.encode())
    fp.write(encoded_data)
    fp.flush()
    fp.close()

    old_from = request['from']
    request['from'] = request['to']
    request['to'] = old_from
    request['params'] = "SUCCESS"
    request['rawdata'] = script.toDictionary()

    return request

def get_ping_info(request, config):

    old_from = request['from']
    request['from'] = request['to']
    request['to'] = old_from

    ping_info = dict()
    ping_info["node-name"] = config["DEFAULT"].get("name", "node")
    ping_info["vessel-version"] = vessel_version
    ping_info["python-version"] = platform.python_version()
    ping_info["python-compiler"] = platform.python_compiler()
    ping_info["operating-system"] = platform.platform()
    ping_info["packages"] = sorted(["%s==%s" % (i.key, i.version) for i in get_installed_distributions()])

    request["rawdata"] = ping_info

    return request


def _get_execute_params_for_engine(engine, script):

    absolute_file_path = script.file_path + os.sep + script.file_name

    script_engine_to_params = {
        'python': [engine.path, absolute_file_path],

        'powershell': [engine.path, '-ExecutionPolicy', 'RemoteSigned',
                        '-F', absolute_file_path],

        'batch': [absolute_file_path],

        'node': [engine.path, absolute_file_path],

        'exe': [absolute_file_path]
    }

    # configured like this allows for users to also override build in engines with their own
    user_engines = [x for x in enginemaps.user_engines if x.name == engine.name]
    if len(user_engines) > 0:
        user_engine = user_engines[0]

        params = list()
        params.append(user_engine["engine_path"])
        params.extend(user_engine["pre_script_parameters"])
        params.append(absolute_file_path)
        params.extend(user_engine["post_script_parameters"])

        return params

    return script_engine_to_params.get(engine.name, [absolute_file_path])


def execute_script(script_execute_list, logger):

    try:
        # execute the script
        process = subprocess.run(script_execute_list, shell=True,
                                 check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                 encoding="utf-8")
        process.check_returncode()  # will throw exception if execution failed

        parsed_output = dict()
        if "-" in process.stdout:
            split_up_response = process.stdout.split("-")
            for section in split_up_response:
                space_index = section.find(" ")
                if space_index != -1:
                    key = section[:space_index]
                    value = section[space_index + 1:]
                    parsed_output[key] = value

        rawdata = dict()
        rawdata["parsed_output"] = parsed_output
        rawdata["data"] = (process.stdout, process.stderr, process.returncode)

        return (True, rawdata)

    except CalledProcessError as cpe:
        logger.exception("A CalledProcessError Occurred")

        rawdata = dict()
        rawdata["parsed_output"] = dict()
        rawdata["data"] = (cpe.stdout, cpe.stderr, cpe.returncode)

        return (False, rawdata)

    except OSError as ose:
        logger.exception()
        logger.error("An OS Error Occurred")

        rawdata = dict()
        rawdata["parsed_output"] = dict()
        rawdata["data"] = (ose.strerror, ose.strerror, ose.errno)

        return (False, rawdata)


def execute_script_on_node(sql_manager, request, logger):
    script_guid = request['rawdata'][1]

    all_scripts = sql_manager.getAllScripts()
    script_found = False
    for script in all_scripts:
        if script.guid == uuid.UUID(script_guid):

            # figure out execution parameters here
            engine = sql_manager.getEngineOfName(script.script_engine)
            execution_params = _get_execute_params_for_engine(engine, script)

            succesful, results_data = execute_script(execution_params, logger)

            if succesful:
                old_from = request['from']
                request['from'] = request['to']
                request['to'] = old_from
                request['params'] = "SUCCESS"
                request['rawdata'] = results_data
            else:
                old_from = request['from']
                request['from'] = request['to']
                request['to'] = old_from
                request['params'] = "FAILED"
                request['rawdata'] = results_data

            return request

    # patch was not found so need to return error
    old_from = request['from']
    request['from'] = request['to']
    request['to'] = old_from
    request['params'] = "FAILED.NOTFOUND"
    request['rawdata'] = "The requested script could not be found"

    return request

def execute_deployment_on_node(sql_manager, request, logger):

    node_guid, deployment_guid = request['rawdata']

    deployment = sql_manager.getDeploymentOfGuid(deployment_guid)
    if deployment is None:
        # there is an error as this does not exist
        old_from = request['from']
        request['from'] = request['to']
        request['to'] = old_from
        request['params'] = "FAILED.NOTFOUND"
        request['rawdata'] = 'The Deployment Of Guid: ' + deployment_guid \
                             + ' Does Not Exist On This Node. Could Not Execute Deployment'

        return request
    # otherwise we are good
    # scripts are returned in order ?
    scripts = sql_manager.getScriptsOfDeploymentGuid(deployment_guid)
    success_data = list()
    for index, script in enumerate(scripts):
        success, exec_results = execute_script(script, logger)

        if not success:
            old_from = request['from']
            request['from'] = request['to']
            request['to'] = old_from
            request['params'] = "FAILED"

            rawdata = dict()
            rawdata["successful"] = success_data
            rawdata["failed_script"] = exec_results
            rawdata["successful_up_to_index"] = index

            request['rawdata'] = rawdata

            return request
        else:
            success_data.append(exec_results)

    old_from = request['from']
    request['from'] = request['to']
    request['to'] = old_from
    request['params'] = "SUCCESS"

    rawdata = dict()
    rawdata["successful"] = success_data
    rawdata["successful_up_to_index"] = len(scripts) - 1

    request['rawdata'] = rawdata

    return request



def create_deployment(sql_manager, request, logger):

    raw_data = request['rawdata']
    node_guid, deployment_name, deployment_description, deployment_script_guids = raw_data

    for deployment_script_guid in deployment_script_guids:

        script = sql_manager.getScriptOfGuid(deployment_script_guid.scriptGuid)
        if script is None:
            # this script guid does not exist, we have an error
            old_from = request['from']
            request['from'] = request['to']
            request['to'] = old_from
            request['params'] = "FAILED"
            request['rawdata'] = 'The Script Of Guid: ' + deployment_script_guid.scriptGuid \
                                 + ' Does Not Exist On This Node. Could Not Create Deployment'

            return request

    # were fine now though

    deployment = Deployment()
    deployment.name = deployment_name
    deployment.description = deployment_description

    deployment = sql_manager.insertDeployment(deployment)

    deployment_dict = deployment.toDictionary()

    inserted_scripts = list()
    for deployment_script_guid in deployment_script_guids:
        script = sql_manager.getScriptOfGuid(deployment_script_guid.scriptGuid)

        deployment_script = DeploymentScript()
        deployment_script.script = script.id
        deployment_script.deployment = deployment.id
        deployment_script.priority = deployment_script_guid.priority

        inserted_deployment_script = sql_manager.insertDeploymentScript(deployment_script)
        inserted_scripts.append(inserted_deployment_script.toDictionary())


    old_from = request['from']
    request['from'] = request['to']
    request['to'] = old_from
    request['params'] = "SUCCESS"
    request['rawdata'] = (deployment_dict, inserted_scripts)

    return request


def fetch_node_deployments(sql_manager, request, logger):
    all_deployments = sql_manager.getAllDeployments()

    all_deployments_as_dict = list()
    for deployment in all_deployments:
        all_deployments_as_dict.append(deployment.toDictionary())

    old_from = request['from']
    request['from'] = request['to']
    request['to'] = old_from
    request['params'] = "SUCCESS"
    request['rawdata'] = all_deployments_as_dict

    return request


def fetch_node_scripts(sql_manager, request, logger):
    all_scripts = sql_manager.getAllScripts()

    all_scripts_as_dict = list()
    for script in all_scripts:
        all_scripts_as_dict.append(script.toDictionary())

    old_from = request['from']
    request['from'] = request['to']
    request['to'] = old_from
    request['params'] = "SUCCESS"
    request['rawdata'] = all_scripts_as_dict

    return request

