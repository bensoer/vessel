import os
from db.models.Script import Script
from db.models.Engine import Engine
import subprocess
from subprocess import CalledProcessError
import utils.enginemaps as enginemaps


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
            engine_name = determine_engine_for_script(script_file)

            # check an engine name could be determined for this script
            if engine_name is None:
                logger.error("Could Not Determine Appropriate Engine For Script: " + str(script_file)
                             + " Script Will Not Be Catalogued")
                continue

            # check the engine for this script is supported by the system
            elif sqlite_manager.getEngineOfName(engine_name) is None:
                logger.error("Engine Is Not Supported or Not Installed On The Node System. " +
                             "Script: " + str(script_file) + " Engine: " + engine_name +
                             ". Script Will Not Be Catalogued")
                continue

            # check if we know about this script already - is it already in the db ?
            if len([known_script for known_script in known_scripts if known_script.file_name == script_file]) == 0:
                # this script is not known - so add it

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


def catalogue_local_engines(sqlite_manager, logger):
    logger.info("Verifying Script Engines Available On System")

    for engine in enginemaps.supported_engines:

        if engine in enginemaps.default_catalogued_engines:
            engine_record = Engine()
            engine_record.name = engine
            engine_record.path = ""

            if sqlite_manager.getEngineOfName(engine) is None:
                sqlite_manager.insertEngine(engine_record)
            continue

        try:
            process = subprocess.run(["where", engine], shell=True, check=True,
                                     stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                     encoding="utf-8")
            process.check_returncode()

            full_engine_path = process.stdout.split('\n')[0] # if we find multiple, we just take the first one
            full_engine_path = full_engine_path.rstrip()

            engine_record = Engine()
            engine_record.name = engine
            engine_record.path = full_engine_path

            if sqlite_manager.getEngineOfName(engine) is None:
                sqlite_manager.insertEngine(engine_record)

        except CalledProcessError as cpe:
            logger.exception("Engine (" + engine + ") Could Not Be Found On System. Making Sure To Remove From Records")

            logger.info("Deleting Engine Record From Database")
            old_known_engine = sqlite_manager.getEngineOfName(engine)
            if old_known_engine is not None:
                sqlite_manager.deleteEngineOfGuid(old_known_engine.guid)

            logger.info("Deleting All Scripts Using Engine From Database")
            for script in sqlite_manager.getAllScripts():
                if script.script_engine == engine:
                    sqlite_manager.deleteScriptOfGuid(script.guid)

    logger.info("Adding User Engines")
    for user_engine in enginemaps.user_engines:

        engine_record = Engine()
        enginemaps.name = user_engine["name"]
        engine_record.path = user_engine["engine_path"]

        if sqlite_manager.getEngineOfName(user_engine["name"]) is None:
            sqlite_manager.insertEngine(engine_record)


def determine_engine_for_script(script_name):

    file_type = script_name[script_name.rfind('.')+1:]

    engine = enginemaps.filetype2engine.get(file_type, None)
    if engine is None:
        user_engine_names = [x.get("name", None) for x in enginemaps.user_engines if file_type in x.get("file_types", None)]
        if len(user_engine_names) > 0 and user_engine_names[0] is not None:
            engine = user_engine_names[0]

    return engine
