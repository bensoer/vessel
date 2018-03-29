import uuid

class Script:

    id = None
    guid = None
    file_name = None
    script_engine = None

    def toDictionary(self):
        return {
            'id': self.id,
            'guid': str(self.guid),
            'file_name': self.file_name,
            'script_engine': self.script_engine
        }

    @staticmethod
    def fromDictionary(dictionary):

        new_script = Script()
        new_script.id = dictionary['id']
        new_script.guid = uuid.UUID(dictionary['guid'])
        new_script.file_name = dictionary['file_name']
        new_script.script_engine = dictionary['script_engine']

        return new_script