import logging
import logging.handlers


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fh = logging.handlers.TimedRotatingFileHandler('logfile.log',
                                               when='D',
                                               interval=1,
                                               backupCount=0,
                                               encoding='utf-8',
                                               delay=False,
                                               utc=False, atTime=None)
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)


# logging decolater
def log(func):
    def wrapper(*args, **kwargs):
        logger.info('START-{}'.format(func.__name__))
        res = func(*args, **kwargs)
        logger.info('END-{}'.format(func.__name__))
        return res
    return wrapper