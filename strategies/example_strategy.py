from strategies.strategy import Strategy

from manifold_api import ManifoldAPI
from manifold_database import ManifoldDatabaseReader
from manifold_subscriber import ManifoldSubscriber

class ExampleStrategy(Strategy):
    def __init__(self, manifold_api, manifold_db_reader, manifold_subscriber):
        super().__init__(name=__name__) 
    
    def run(self):
        # Find users who made the most profit today
        self.db.insert({"hi", 1})
        
       
       