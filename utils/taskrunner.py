import uuid
import subprocess
from subprocess import CalledProcessError
import json
from db.models.Script import Script


def migrate(root_dir, sql_manager, request, logger):

    node_guid, serialized_script = request['params']
    script = Script.fromDictionary(serialized_script)
    script.id = sql_manager.insertScript(script)

    file_path = root_dir + "/scripts/" + script.file_name
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

def execute_script_on_node(root_dir, sql_manager, request, logger):
    script_guid = request['rawdata'][1]

    all_scripts = sql_manager.getAllScripts()
    script_found = False
    for script in all_scripts:
        if script.guid == uuid.UUID(script_guid):
            script_found = True
            try:

                # execute the script
                absolute_file_path = root_dir + "/scripts/" + script.file_name
                process = None
                if script.script_engine == "":
                    process = subprocess.run([absolute_file_path], shell=True, check=True,
                                             stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                             encoding="utf-8")
                else:
                    process = subprocess.run([script.script_engine, absolute_file_path], shell=True,
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