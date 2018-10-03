
class Execution:

    id = None
    guid = None
    time = None
    script_guid = None
    stdout = None
    stderr = None
    return_code = None
    successful = None

    def toDictionary(self):
        return {
            'id': self.id,
            'guid': str(self.guid),
            'time': self.time,
            'script_guid': str(self.script_guid),
            'stdout': str(self.stdout),
            'stderr': str(self.stderr),
            'return_code': self.return_code,
            'successful': self.successful
        }