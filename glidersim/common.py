import logging


def get_logger(name):
    logger = logging.getLogger(name=name)
    logger.setLevel(logging.INFO)
    return logger

    
