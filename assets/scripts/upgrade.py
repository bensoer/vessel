import subprocess
import os
import sys
import inspect

service_name = sys.argv[1]
project_root = os.path.abspath(inspect.getfile(inspect.currentframe())) + ".." + os.sep + ".. " + os.sep


process = subprocess.run(["where", "python"], shell=True, check=True,
                                     stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                     encoding="utf-8")
process.check_returncode()

full_python_path = process.stdout.split('\n')[0] # if we find multiple, we just take the first one
full_python_path = full_python_path.rstrip()


process = subprocess.run(["where", "git"], shell=True, check=True,
                                     stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                     encoding="utf-8")
process.check_returncode()

full_git_path = process.stdout.split('\n')[0] # if we find multiple, we just take the first one
full_git_path = full_git_path.rstrip()

if service_name == "VesselNode":

    # stop the service
    stop_p = subprocess.Popen([full_python_path, project_root + "node.py", "stop"])
    stop_p.wait()

    # uninstall the service
    uninstall_p = subprocess.Popen([full_python_path, project_root + "node.py", "remove"])
    uninstall_p.wait()

    # git pull: https://github.com/bensoer/vessel
    git_p = subprocess.Popen([full_git_path, "-C", project_root, "pull", "origin", "master"])

    # install the service
    install_p = subprocess.Popen([full_python_path, project_root + "node.py", "install"])
    install_p.wait()

    # start the service
    start_p = subprocess.Popen([full_python_path, project_root + "node.py", "start"])
    start_p.wait()


elif service_name == "VesselService":

    # stop the service
    stop_p = subprocess.Popen([full_python_path, project_root + "master.py", "stop"])
    stop_p.wait()

    # uninstall the service
    uninstall_p = subprocess.Popen([full_python_path, project_root + "master.py", "remove"])
    uninstall_p.wait()

    # git pull: https://github.com/bensoer/vessel
    git_p = subprocess.Popen([full_git_path, "-C", project_root, "pull", "origin", "master"])

    # install the service
    install_p = subprocess.Popen([full_python_path, project_root + "master.py", "install"])
    install_p.wait()

    # start the service
    start_p = subprocess.Popen([full_python_path, project_root + "master.py", "start"])
    start_p.wait()

