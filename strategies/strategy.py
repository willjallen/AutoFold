from tinydb import TinyDB, Query

class Strategy():
    def __init__(self, name: str):
        self.db = TinyDB(name) 