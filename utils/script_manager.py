import os
from db.models.Script import Script


def catalogue_path(path, known_scripts, sqlite_manager, logger):
    logger.info("Cataloguing At Root Path : " + path)

    script_files = os.listdir(path)

    for script_file in script_files:
        new_path = path + os.sep + script_file
        logger.info("File Or Dir In Path Is: " + new_path)

        if os.path.isdir(new_path):
            logger.info("This Path Is A Dir. Recursing...")
            catalogue_path(new_path, known_scripts, sqlite_manager, logger)
        else:
            if len([known_script for known_script in known_scripts if known_script.file_name == script_file]) == 0:
                # this script is not known
                engine_name = determine_engine_for_script(script_file)

                if engine_name is None:
                    logger.error("Could Not Determine Appropriate Engine For Script: " + str(script_file)
                                       + " Script Will Not Be Catalogued")
                    continue

                script = Script()
                script.file_name = script_file
                script.script_engine = engine_name
                script.file_path = path
                sqlite_manager.insertScript(script)


def catalogue_local_scripts(sqlite_manager, script_dir, logger):
    logger.info("Searching For New Scripts On The System")
    known_scripts = sqlite_manager.getAllScripts()

    logger.info("Fetching Paths From Config")
    paths = script_dir.split(";")
    logger.info(paths)
    for path in paths:
        logger.info("Catalogueing Path: >" + path + "<")
        if path != "":  # happens if the user leaves a trailing semi-colon
            logger.info("Path Is Valid: >" + path + "<")
            catalogue_path(path, known_scripts, sqlite_manager, logger)

    logger.info("Removing Record Entries For Scripts No Longer On The System")
    for known_script in known_scripts:
        if not os.path.isfile(known_script.file_path + os.sep + known_script.file_name):
            logger.info("Script No Longer Exists. Deleting From DB: " + known_script.file_path + os.sep
                        + known_script.file_name)
            sqlite_manager.deleteScriptOfId(known_script.id)


def determine_engine_for_script(script_name):

    filetype2engine = {
        'ps1': 'powershell',
        'py': 'python',
        'sql': 'sql',
        'bat': 'batch',
        'exe': 'exe',
        'js': 'node'
    }

    file_type = script_name[script_name.rfind('.')+1:]
    return filetype2engine.get(file_type, None)