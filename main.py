import json
import time
import requests
from datetime import datetime
import sqlite3

from manifold_api import ManifoldAPI


def main():
    manifold_api = ManifoldAPI()
    
    data_future_1 = manifold_api.get_user_by_username("whalelangbot")
    data_future_2 = manifold_api.get_user_by_username("whalelangbot")
    data_future_3 = manifold_api.get_user_by_username("whalelangbot")
    
    print(data_future_1.result(), data_future_2.result(), data_future_3.result())
    

if __name__ == "__main__":
    main()

