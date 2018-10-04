

class Ping:

    id = None
    guid = None
    node_guid = None
    send_time = -1
    recv_time = -1

    def toDictionary(self):
        return {
            'id': str(self.id),
            'guid': str(self.guid),
            'node_guid': str(self.node_guid),
            'send_time': self.send_time,
            'recv_time': self.recv_time
        }