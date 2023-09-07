from loguru import logger

from manifold_api import ManifoldAPI
from manifold_database import ManifoldDatabase
from manifold_database import ManifoldDatabaseReader
from manifold_database import ManifoldDatabaseWriter
from manifold_subscriber import ManifoldSubscriber

from bot import Bot

def main():
    manifold_api = ManifoldAPI()
    
    manifold_db = ManifoldDatabase()
    manifold_db_reader = ManifoldDatabaseReader(manifold_db)
    manifold_db_writer = ManifoldDatabaseWriter(manifold_db)
    manifold_db.create_tables()
    
    manifold_subscriber = ManifoldSubscriber(manifold_api, manifold_db, manifold_db_writer)
    
    bot = Bot(manifold_api, manifold_db_reader, manifold_subscriber, [])
    
    bot.start()
    
    # Keep main thread from exiting
    print("Type e to exit")
    while True:
        inp = input()
        if inp == 'e':
            break


if __name__ == "__main__":
    main()

