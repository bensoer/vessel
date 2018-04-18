
class Deployment:
    id = None
    guid = None
    name = None
    description = None

    def toDictionary(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'guid': str(self.guid)
        }