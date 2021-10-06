import os
import logging
import logging.config
from dotenv import load_dotenv

load_dotenv()
parent_path = os.path.abspath(os.getcwd())
logging.config.fileConfig(parent_path+'/logConfig.conf')

if os.getenv('LOGGER'):
    logger = logging.getLogger(os.getenv('LOGGER'))
else:
    logger = logging.getLogger(__name__)
    