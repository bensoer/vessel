import logging
from logging.handlers import QueueHandler
from db import SQLiteManager

class RecurringTaskProcess:

    child_pipe = None
    logging_queue = None

    known_recurring_tasks = dict()

    def __init__(self, initialization_tuple):
        child_pipe, config, logging_queue = initialization_tuple

        self.child_pipe = child_pipe
        self.logging_queue = logging_queue

        qh = logging.handlers.QueueHandler(logging_queue)
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.addHandler(qh)

        self.logger = logging.getLogger("RecurringTaskProcessLogger")
        self.logger.setLevel(logging.DEBUG)

        self._sql_manager = SQLiteManager(config, self.logger)

    def start(self):

        # while loop
        while True:
            # check the database for any added or removed recurring tasks
            for recurring_task in self._sql_manager.getAllRecurringTasks():

                # register or remove the recurring tasks

                # hang until next task OR timeout - timeout every 10 minutes ?



