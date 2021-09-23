import logging
from logging.handlers import TimedRotatingFileHandler
import datetime
import pytz

class Logger:
    def __init__(self):
        utc_now = datetime.datetime.now(tz=pytz.timezone('UTC'))
        mst_now = utc_now.astimezone(pytz.timezone('Asia/Taipei'))
        logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt=mst_now.strftime('%m/%d/%Y, %H:%M:%S'),
                        handlers=[TimedRotatingFileHandler(f'logs/{mst_now.strftime("%m-%d-%Y")}',when="D", interval=1, backupCount=15,
                                                        encoding="UTF-8", delay=False),])
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
    def debug(self, string):
        return self.logger.debug(string)
    
    def info(self, string):
        return self.logger.info(string)
    
    def warning(self, string):
        return self.logger.warning(string)
    
    def error(self, string):
        return self.logger.error(string)
    
    def critical(self, string):
        return self.logger.critical(string)

