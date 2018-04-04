import uuid
import subprocess
from subprocess import CalledProcessError
import json
from db.models.Script import Script
import os


def migrate(root_dir, sql_manager, request, logger):

    node_guid, serialized_script = request['params']
    script = Script.fromDictionary(serialized_script)
    script.id = sql_manager.insertScript(script)

    file_path = root_dir + os.sep + "scripts" + os.sep + script.file_name
    fp = open(file_path, 'wb+')
    file_data = request['rawdata']
    fp.write(file_data)
    fp.flush()
    fp.close()

    old_from = request['from']
    request['from'] = request['to']
    request['to'] = old_from
    request['param'] = "SUCCESS"
    request['rawdata'] = script

    return request


def _get_execute_params_for_engine(root_dir, script_engine, file_name):

    absolute_file_path = root_dir + os.sep + "scripts" + os.sep + file_name

    script_engine_to_params = {
        'python': ['python', absolute_file_path],
        'powershell': ['powershell.exe', '-ExecutionPolicy', 'RemoteSigned', '-F', absolute_file_path],
        'batch': [absolute_file_path],
        'node': ['node', absolute_file_path],
        'exe': [absolute_file_path]
    }

    return script_engine_to_params.get(script_engine, [absolute_file_path])



def execute_script_on_node(root_dir, sql_manager, request, logger):
    script_guid = request['rawdata'][1]

    all_scripts = sql_manager.getAllScripts()
    script_found = False
    for script in all_scripts:
        if script.guid == uuid.UUID(script_guid):
            script_found = True
            try:
                script_execute_list = _get_execute_params_for_engine(root_dir, script.script_engine, script.file_name)
                # execute the script
                process = subprocess.run(script_execute_list, shell=True,
                                         check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                         encoding="utf-8")
                process.check_returncode()  # will throw exception if execution failed

                old_from = request['from']
                request['from'] = request['to']
                request['to'] = old_from
                request['param'] = "SUCCESS"
                request['rawdata'] = (process.stdout, process.stderr, process.returncode)

                return request

            except CalledProcessError as cpe:
                logger.exception("A CalledProcessError Occurred")
                old_from = request['from']
                request['from'] = request['to']
                request['to'] = old_from
                request['param'] = "FAILED"
                request['rawdata'] = str(cpe.cmd) + " \n\n " + str(cpe.output) + " \n\n " + str(cpe.returncode)

                return request

            except OSError as ose:
                logger.exception()
                logger.error("An OS Error Occurred")

                old_from = request['from']
                request['from'] = request['to']
                request['to'] = old_from
                request['param'] = "FAILED"
                request['rawdata'] = str(ose.cmd) + " \n\n " + str(ose.output) + " \n\n " + str(
                    ose.returncode)

                return request

    if not script_found:
        old_from = request['from']
        request['from'] = request['to']
        request['to'] = old_from
        request['param'] = "FAILED"
        request['rawdata'] = "The request script could not be found"

        return request


def fetch_node_scripts(sql_manager, request, logger):
    all_scripts = sql_manager.getAllScripts()

    all_scripts_as_dict = list()
    for script in all_scripts:
        all_scripts_as_dict.append(script.toDictionary())

    old_from = request['from']
    request['from'] = request['to']
    request['to'] = old_from
    request['rawdata'] = all_scripts_as_dict

    return request