from tinydb import TinyDB, Query
from strategies.strategy import Strategy
from bot import Bot
from manifold.manifold_api import ManifoldAPI
from manifold.manifold_database import ManifoldDatabaseReader
from manifold.manifold_subscriber import ManifoldSubscriber

class TemplateStrategy(Strategy):
    def __init__(self, bot: Bot, manifold_api: ManifoldAPI, manifold_db_reader: ManifoldDatabaseReader, manifold_subscriber: ManifoldSubscriber):
        super().__init__(name=__name__)
        self.bot = bot
        self.manifold_api = manifold_api
        self.manifold_db_reader = manifold_db_reader
        self.manifold_subscriber = manifold_subscriber
        
    def run(self):
        pass
    
    def shutdown(self):
        pass