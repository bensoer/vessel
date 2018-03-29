class Node:

    id = None
    name = None
    ip = None
    key_guid = None
    guid = None
    port = None

    def toDictionary(self):
        return {
            'id':self.id,
            'name':self.name,
            'ip':self.ip,
            'port':self.port,
            'key_guid':str(self.key_guid),
            'guid':str(self.guid)
        }