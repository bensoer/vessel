
class Engine:

    id = None
    guid = None
    name = None
    path = None

    def toDictionary(self):
        return {
            'id': self.id,
            'name': self.name,
            'guid': str(self.guid),
            'path': self.path
        }