
class DeploymentScript:
    id = None
    deployment = None
    script = None
    priority = None

    def toDictionary(self):
        return {
            'id': self.id,
            'deployment': self.deployment,
            'script': self.script,
            'priority': self.priority
        }