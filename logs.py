import logging
import os

def logs_dir():
    """
    Создание директории с логами.
    """
    path = os.getcwd()
    n_dir = "/logs"
    try:
        os.mkdir(path+n_dir)
    except OSError:
        pass
        
def logger_init():
    """
    Инициализация логгинга.
    """
    logs_dir()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s:%(name)s:%(asctime)s:%(message)s')
    file_handler = logging.handlers.RotatingFileHandler('logs/log.log', mode='a', maxBytes=1*1024*1024, 
                                 backupCount=50, encoding=None, delay=0)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
