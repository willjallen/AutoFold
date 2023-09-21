from loguru import logger
import signal
import time


from manifold.manifold_api import ManifoldAPI
from manifold.manifold_database import ManifoldDatabase
from manifold.manifold_database import ManifoldDatabaseReader
from manifold.manifold_database import ManifoldDatabaseWriter
from manifold.manifold_subscriber import ManifoldSubscriber

from bot import Bot

SHUTDOWN = False

def graceful_shutdown(sig, frame):
    global SHUTDOWN
    SHUTDOWN = True # Signal threads to shut down



def main():
   
    # Logging
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    # Configure the logger
    logger.add("logs/{time:YYYY-MM-DD}.log", rotation="1 day", format=log_format, level="TRACE", enqueue=True) 
    # logger.add(lambda msg: print(msg), format=log_format, level="INFO") 

    logger.info("Logging has been set up!") 
    
    # Bind Ctrl+C to the graceful_shutdown function
    signal.signal(signal.SIGINT, graceful_shutdown) 
    
    manifold_api = ManifoldAPI()
    
    manifold_db = ManifoldDatabase()
    manifold_db_reader = ManifoldDatabaseReader(manifold_db)
    manifold_db_writer = ManifoldDatabaseWriter(manifold_db)
    manifold_db.create_tables()
    
    manifold_subscriber = ManifoldSubscriber(manifold_api, manifold_db, manifold_db_writer)
    
    bot = Bot(manifold_api, manifold_db_reader, manifold_subscriber)
    
    bot.start()
    
    # Keep main thread from exiting
    print("ctrl+c to exit")
    global SHUTDOWN
    while not SHUTDOWN:
        time.sleep(1)
   
    logger.info("Shutting down...") 
    
    # Api must be shut down first
    manifold_api.shutdown()

    # Bot
    bot.shutdown()

    # Subscriber
    manifold_subscriber.shutdown()

    # Database 
    manifold_db_writer.shutdown()

if __name__ == "__main__":
    main()

