import logging

def logger(log_name='SmartTrading'):
    logger = logging.getLogger(log_name)
    FORMAT = "Logger |%(filename)s (%(lineno)s): %(funcName)s()| %(message)s"
    logging.basicConfig(format=FORMAT)
    logger.setLevel(logging.DEBUG)
    return logger