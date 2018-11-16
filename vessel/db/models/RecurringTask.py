

class RecurringTask:

    id = None
    guid = None
    script_guid = None
    node_guid = None
    cron = None

    def toDictionary(self):
        return {
            'id': self.id,
            'guid': str(self.guid),
            'script_guid': str(self.script_guid),
            'node_guid': str(self.node_guid),
            'cron': self.cron
        }