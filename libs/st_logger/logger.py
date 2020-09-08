import logging

def logger(log_name='SmartTrading'):
    logging.basicConfig()
    logging.root.setLevel(logging.NOTSET)
    logging.basicConfig(level=logging.NOTSET)
    logger = logging.getLogger(log_name)
    return logger