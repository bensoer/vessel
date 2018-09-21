'''
filetype2engine is a dictionary mapping file extensions to thier appropriate engine. Vessel uses this mapping when
catalogueing scripts and to determine if there is a supported engine that exists on the system. Edit this mapping
to include or exclude certain file types and their matching engine Vessel should use when executing them
'''
filetype2engine = {
        'ps1':'powershell',
        'py': 'python',
        'bat': 'batch',
        'exe': 'exe',
        'js': 'node'
    }
'''
supported_engines are all the engines currently supported on Vessel. All scripts must map to one of these engines
otherwise it will not be catalogued by Vessel. 

WARNING: Engines can be added to this list and Vessel will catalogue all files mapped to it in the filetype2engine
dictionary. However, when executing, Vessel will use the default execution process which will be to launch a
terminal and execute the scripts full path on it. The user will have to ensure the executing node has the required
engine installed and configured in the PATH and is setup to be default called when the engine's script type is
executed. Use user_engines for better options in configuring a 3rd party engine
'''
supported_engines = ["python", "exe", "powershell", "node", "batch"]

'''
default_catalogues_engines are all the engines which are automatically accepted as valid and available on the
end system. Vessel will not check the system if it can find programs that can execute the engine types listed
within this list
'''
default_catalogued_engines = ["exe", "batch"]


'''
user_engines are for 3rd party engines which have not had support added natively to Vessel. user_engines is for
users to add additional engine and script support to Vessel ahead of Vessel's development. user_engines is a 
list containing dictionaries. An example of user_engines configured with a perl engine may look like this:

user_engines = [
    {
        'name':'perl',
        'engine_path':'C:\perl\perl.exe',
        'pre_script_parameters': [],
        'post_script_parameters': [],
        'file_types':['pl', 'pld', 'plc']
    }
]

Once an engine has been added, you can then add its file type mappings in the filetype2engine dictionary above

When Vessel executes a script belonging to a user engine it will be executed in a terminal as:
~$: <engine_path> <pre_script_parameters> <script> <post_script_parameters>
For the above perl example. Running the script helloworld.pl would be run like this:
~$: C:\perl\perl.exe helloworld.pl
Because the pre and post script parameter string arrays are empty, nothing is used

NOTE: Adding multiple user_engines will have a small performance hit as Vessel only checks this array after
failing to successfully use engines listed in supported_engines.
'''
user_engines = []

