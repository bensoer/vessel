import logging
from logging.handlers import RotatingFileHandler
from multiprocessing import Queue
import threading

master_logger = None
node_logger = None
node_listener_process_logger = None
node_client_process_logger = None
http_listener_process_logger = None
terminal_listener_process_logger = None

logging_queue = Queue()


def logging_thread(queue):
    while True:
        record = queue.get()
        if record is None:
            break
        logger = logging.getLogger(record.name)
        logger.handle(record)


def initialize_all_logging_configuration(log_dir):
    global master_logger
    global node_listener_process_logger
    global http_listener_process_logger
    global terminal_listener_process_logger
    global node_logger
    global node_client_process_logger

    node_logpath = log_dir + "/node-service.log"
    master_logpath = log_dir + "/master-service.log"
    node_listener_process_logpath = log_dir + "/node-listener-process.log"
    http_listener_process_logpath = log_dir + "/http-listener-process.log"
    terminal_listener_process_logpath = log_dir + "/terminal-listener-process.log"
    node_client_process_logpath = log_dir + "/node-client-process.log"

    node_logger = logging.getLogger("NodeProcessLogger")
    node_logger.setLevel(logging.DEBUG)
    node_handler = RotatingFileHandler(node_logpath, maxBytes=8192, backupCount=10)
    node_format = logging.Formatter(
        '%(name)s@%(asctime)s : %(filename)s -> %(funcName)s - %(levelname)s - %(message)s'
    )
    node_handler.setFormatter(node_format)
    node_logger.addHandler(node_handler)

    master_logger = logging.getLogger("MasterProcessLogger")
    master_logger.setLevel(logging.DEBUG)
    master_handler = RotatingFileHandler(master_logpath, maxBytes=8192, backupCount=10)
    master_format = logging.Formatter(
        '%(name)s@%(asctime)s : %(filename)s -> %(funcName)s - %(levelname)s - %(message)s')
    master_handler.setFormatter(master_format)
    master_logger.addHandler(master_handler)

    node_listener_process_logger = logging.getLogger("NodeListenerProcessLogger")
    node_listener_process_logger.setLevel(logging.DEBUG)
    node_listener_process_handler = RotatingFileHandler(node_listener_process_logpath, maxBytes=8192, backupCount=10)
    node_listener_process_format = logging.Formatter(
        '%(name)s@%(asctime)s : %(filename)s -> %(funcName)s - %(levelname)s - %(message)s')
    node_listener_process_handler.setFormatter(node_listener_process_format)
    node_listener_process_logger.addHandler(node_listener_process_handler)

    node_client_process_logger = logging.getLogger("NodeClientProcessLogger")
    node_client_process_logger.setLevel(logging.DEBUG)
    node_client_process_handler = RotatingFileHandler(node_client_process_logpath, maxBytes=8192, backupCount=10)
    node_client_process_format = logging.Formatter(
        '%(name)s@%(asctime)s : %(filename)s -> %(funcName)s - %(levelname)s - %(message)s'
    )
    node_handler.setFormatter(node_client_process_format)
    node_logger.addHandler(node_client_process_handler)

    http_listener_process_logger = logging.getLogger("HttpListenerProcessLogger")
    http_listener_process_logger.setLevel(logging.DEBUG)
    http_listener_process_handler = RotatingFileHandler(http_listener_process_logpath, maxBytes=8192, backupCount=10)
    http_listener_process_format = logging.Formatter(
        '%(name)s@%(asctime)s : %(filename)s -> %(funcName)s - %(levelname)s - %(message)s')
    http_listener_process_handler.setFormatter(http_listener_process_format)
    http_listener_process_logger.addHandler(http_listener_process_handler)

    terminal_listener_process_logger = logging.getLogger("TerminalListenerProcessLogger")
    terminal_listener_process_logger.setLevel(logging.DEBUG)
    terminal_listener_process_handler = RotatingFileHandler(terminal_listener_process_logpath, maxBytes=8192,
                                                            backupCount=10)
    terminal_listener_process_format = logging.Formatter(
        '%(name)s@%(asctime)s : %(filename)s -> %(funcName)s - %(levelname)s - %(message)s')
    terminal_listener_process_handler.setFormatter(terminal_listener_process_format)
    terminal_listener_process_logger.addHandler(terminal_listener_process_handler)


def start_logging_thread():
    l_thread = threading.Thread(target=logging_thread,
                                args=(logging_queue,))
    l_thread.daemon = True
    l_thread.start()

    return l_thread
