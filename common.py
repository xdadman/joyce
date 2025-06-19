from datetime import datetime, timezone
from pymodbus import pymodbus_apply_logging_config
import logging
import sys, os
from multiprocessing import Queue

from logging.handlers import TimedRotatingFileHandler

USE_LOKI = False
USE_FILES = True
USE_STDOUT = True

class RFC3339Formatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        #dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def setup_logging(log_level: int):
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.setLevel(log_level)
        return
    #    for handler in root_logger.handlers:
#            root_logger.removeHandler(handler)

    #formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s — %(message)s")
    formatter = RFC3339Formatter('%(asctime)s %(name)s %(levelname)s - %(message)s')

    root_logger.setLevel(log_level)

    if USE_LOKI:
        import logging_loki
        handler = logging_loki.LokiQueueHandler(
            Queue(-1),
            url="http://192.168.3.14:3100/loki/api/v1/push",
            tags={"application": "my-app", "esi_no": "1"},
            auth=("username", "password"),
            version="1",
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    if USE_FILES:
        log_path = "./logs"
        if not os.path.isdir(log_path):
            root_logger.error("No 'logs' directory exists")
            raise Exception("No 'logs' directory exists")
        filename = "esi.log"
        file_handler = logging.FileHandler("{0}/{1}".format(log_path, filename))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    logging.getLogger('aiokafka.conn').setLevel(logging.ERROR)
    # usefull configurations
    # logging.getLogger('aiokafka').setLevel(logging.INFO)
    # logging.getLogger('pymodbus.payload').setLevel(logging.DEBUG)
    # logging.getLogger('pymodbus.transaction').setLevel(logging.DEBUG)
    # logging.getLogger('pymodbus.framer').setLevel(logging.DEBUG)
    # logging.getLogger('pymodbus.factory').setLevel(logging.INFO)
    # logging.getLogger('pymodbus.client').setLevel(logging.INFO)
    # logging.getLogger('pymodbus.logging').setLevel(logging.DEBUG)
    # logging.getLogger('registers').setLevel(logging.INFO)

    if USE_STDOUT:
        _console_handler = logging.StreamHandler(sys.stdout)
        _console_handler.setFormatter(formatter)
        root_logger.addHandler(_console_handler)

    pymodbus_apply_logging_config(log_level)

def get_date_iso_str():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
