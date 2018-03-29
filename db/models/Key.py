class Key:

    id = None
    name = None
    description = ""
    guid = None
    key = None

    def toDictionary(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'guid': str(self.guid),
            'key': self.key
        }
