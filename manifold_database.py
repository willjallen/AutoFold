import json
import sqlite3
import threading
import time

from utils.str_utils import collapse_list_of_strings_to_string
import concurrent.futures

# Helper function for multiple upserts
def prepare_and_execute_multi_upsert(conn, query, fields, data):
    query_fields = ", ".join(fields)
    query_placeholders = ", ".join("?" for _ in fields)
    sql_query = query.format(fields=query_fields, placeholders=query_placeholders)
    values_tuple = [tuple(data.get(field, None) for field in fields) for data in data]
    conn.executemany(sql_query, values_tuple)

# Helper function for multiple deletions
def prepare_and_execute_multi_deletion(conn, query, ids):
    # Check if the first item in ids is a tuple
    if isinstance(ids[0], tuple):
        values_tuple = ids
    else:
        values_tuple = [(item,) for item in ids]

    conn.executemany(query, values_tuple)
    



class ManifoldDatabase:
    def __init__(self):
        self.local_storage = threading.local()

    def get_conn(self):
        if not hasattr(self.local_storage, "conn"):
            self.local_storage.conn = sqlite3.connect("dbs/manifold_database.db")
            self.local_storage.conn.execute("PRAGMA journal_mode=WAL;")
        return self.local_storage.conn

    def create_tables(self):
        conn = self.get_conn()
        
        '''
        ########################################################
        ####                    USERS                       ####
        ########################################################
        '''
        # Create users table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            createdTime INTEGER,
            name TEXT,
            username TEXT,
            url TEXT,
            bio TEXT,
            balance REAL,
            totalDeposits REAL,
            totalPnLCached REAL,
            retrievedTimestamp INTEGER
        );
        """)
        
        '''
        ########################################################
        ####                    MARKETS                     ####
        ########################################################
        '''
        # Create binary markets table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS binary_choice_markets (
            id TEXT PRIMARY KEY,
            closeTime INTEGER,
            createdTime INTEGER,
            creatorId TEXT,
            creatorName TEXT,
            creatorUsername TEXT,
            isResolved BOOLEAN,
            lastUpdatedTime INTEGER,
            mechanism TEXT,
            outcomeType TEXT,
            p REAL,
            probability REAL,
            question TEXT,
            textDescription TEXT,
            totalLiquidity REAL,
            url TEXT,
            volume REAL,
            volume24Hours REAL,
            pool_NO REAL,
            pool_YES REAL,
            groupSlugs TEXT,
            retrievedTimestamp INTEGER,
            lite INTEGER
        );
        """)
        
        # Create multiple choice markets table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS multiple_choice_markets (
            id TEXT PRIMARY KEY,
            closeTime INTEGER,
            createdTime INTEGER,
            creatorId TEXT,
            creatorName TEXT,
            creatorUsername TEXT,
            isResolved BOOLEAN,
            lastUpdatedTime INTEGER,
            mechanism TEXT,
            outcomeType TEXT,
            question TEXT,
            textDescription TEXT,
            totalLiquidity REAL,
            volume REAL,
            volume24Hours REAL,
            url TEXT,
            groupSlugs TEXT,
            retrievedTimestamp INTEGER,
            lite INTEGER
        );
        """)

        # Create 'nested' answers table for multiple choice markets
        conn.execute("""
        CREATE TABLE IF NOT EXISTS multiple_choice_market_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contractId TEXT,
            createdTime INTEGER,
            fsUpdatedTime TEXT,
            isOther INTEGER,
            answerIndex INTEGER,
            probability REAL,
            subsidyPool REAL,
            text TEXT,
            totalLiquidity REAL,
            userId TEXT,
            pool_NO REAL,
            pool_YES REAL,
            FOREIGN KEY(contractId) REFERENCES multiple_choice_markets(id)
        ); 
        """)

        '''
        ########################################################
        ####                 CONTRACT METRICS               ####
        ########################################################
        '''
        # Create contract_metrics table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS contract_metrics (
            contractId TEXT,
            hasNoShares INTEGER,
            hasShares INTEGER,
            hasYesShares INTEGER,
            invested REAL,
            loan REAL,
            maxSharesOutcome TEXT,
            payout REAL,
            profit REAL,
            profitPercent REAL,
            userId TEXT,
            userUsername TEXT,
            userName TEXT,
            lastBetTime INTEGER,
            retrievedTimestamp INTEGER,
            PRIMARY KEY (contractId, userId) 
        );
        """)
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS contract_metrics_from (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contractId TEXT,
            userId TEXT,
            period TEXT,
            value REAL,
            profit REAL,
            invested REAL,
            prevValue REAL,
            profitPercent REAL,
            FOREIGN KEY (contractId, userId) REFERENCES contract_metrics(contractId, userId)
        ); 
        """)

        # contract_metrics_totalShares table to represent 'totalShares' nested structure
        conn.execute("""
        CREATE TABLE IF NOT EXISTS contract_metrics_totalShares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contractId TEXT,
            userId TEXT,
            outcome TEXT,
            numberOfShares REAL,
            FOREIGN KEY (contractId, userId) REFERENCES contract_metrics(contractId, userId)
        ); 
        """)

        '''
        ########################################################
        ####                    BETS                        ####
        ########################################################
        '''
        # Create bets table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id TEXT PRIMARY KEY,
            userId TEXT,
            contractId TEXT,
            isFilled INTEGER,
            amount REAL,
            probBefore REAL,
            isCancelled INTEGER,
            outcome TEXT,
            shares REAL,
            limitProb REAL,
            loanAmount REAL,
            orderAmount REAL,
            probAfter REAL,
            createdTime INTEGER,
            retrievedTimestamp INTEGER
        );
        """)

        # Create fees table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS bet_fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            betId TEXT,
            creatorFee REAL,
            liquidityFee REAL,
            platformFee REAL,
            FOREIGN KEY (betId) REFERENCES bets(id)
        );
        """)

        # Create fills table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS bet_fills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            betId TEXT,
            timestamp INTEGER,
            matchedBetId TEXT,
            amount REAL,
            shares REAL,
            FOREIGN KEY (betId) REFERENCES bets(id)
        );
        """)

        conn.commit()
        
    '''
    ########################################################
    ####                    USERS                       ####
    ########################################################
    '''

    def upsert_users(self, users: list[dict]):
        # Get database connection
        conn = self.get_conn()
        
        # Current UNIX epoch time for all markets in this batch
        current_time = int(time.time())
        
        # Begin transaction
        conn.execute("BEGIN TRANSACTION;")
        
        try:
            # Base table fields
            base_fields = [
                    "id", "createdTime", "name", "username", 
                    "url", "bio", "balance", "totalDeposits", 
                    "totalPnLCached", "retrievedTimestamp"
                ]
            
            # Insert or Replace into the base table
            prepare_and_execute_multi_upsert(
                conn=conn,
                query="INSERT OR REPLACE INTO users ({fields}) VALUES ({placeholders})",
                fields=base_fields,
                data=[
                    {**user, 
                     "retrievedTimestamp": current_time,
                    } for user in users],
            )
            
            
            # Commit transaction
            conn.commit()
    
        except sqlite3.Error as e:
            print("Database error in upset_users:", e)
            conn.rollback()  # Rollback transaction in case of error        


    
    '''
    ########################################################
    ####                    MARKETS                     ####
    ########################################################
    '''

    # Upsert Market
    def upsert_binary_choice_markets(self, markets: list[dict], lite=True):
            # Get database connection
            conn = self.get_conn()
            
            # Current UNIX epoch time for all markets in this batch
            current_time = int(time.time())
            
            # Begin transaction
            conn.execute("BEGIN TRANSACTION;")
            
            try:
                # Base table fields
                base_fields = [
                    "id", "closeTime", "createdTime", "creatorId", "creatorName", 
                    "creatorUsername", "isResolved", "lastUpdatedTime", "mechanism", 
                    "outcomeType", "p", "probability", "question", "textDescription", 
                    "totalLiquidity", "volume", "volume24Hours", "url", "pool_NO",
                    "pool_YES", "groupSlugs", "retrievedTimestamp", "lite"
                ]
                
                # Insert or Replace into the base table
                prepare_and_execute_multi_upsert(
                    conn=conn,
                    query="INSERT OR REPLACE INTO binary_choice_markets ({fields}) VALUES ({placeholders})",
                    fields=base_fields,
                    data=[
                        {**market, 
                        "retrievedTimestamp": current_time,
                        "lite": int(lite),
                        "groupSlugs": collapse_list_of_strings_to_string(market.get("groupSlugs", "")),
                        "pool_NO": market.get("pool", {}).get("NO", None),
                        "pool_YES": market.get("pool", {}).get("YES", None)
                        } for market in markets],
                )
                
                # Commit transaction
                conn.commit()
        
            except sqlite3.Error as e:
                print("Database error in upsert_binary_choice_markets:", e)
                conn.rollback()  # Rollback transaction in case of error


    def upsert_multiple_choice_markets(self, markets: list[dict], lite=True):
        # Get database connection
        conn = self.get_conn()
        
        # Current UNIX epoch time for all markets in this batch
        current_time = int(time.time())
        
        # Begin transaction
        conn.execute("BEGIN TRANSACTION;")
        
        try:
            # Base table fields
            base_fields = [
                "id", "closeTime", "createdTime", "creatorId", "creatorName", 
                "creatorUsername", "isResolved", "lastUpdatedTime", "mechanism", 
                "outcomeType", "question", "textDescription", 
                "totalLiquidity", "volume", "volume24Hours", 
                "url", "groupSlugs", "retrievedTimestamp", "lite"
            ]
            
            # Insert or Replace into the base table
            prepare_and_execute_multi_upsert(
                conn=conn,
                query="INSERT OR REPLACE INTO multiple_choice_markets ({fields}) VALUES ({placeholders})",
                fields=base_fields,
                data=[
                    {**market, 
                     "retrievedTimestamp": current_time,
                     "lite": int(lite),
                     "groupSlugs": collapse_list_of_strings_to_string(market.get("groupSlugs", ""))
                    } for market in markets],
            )
            
            # Handle nested tables (answers)
            if not lite:
                
                # Delete existing answers for the markets
                prepare_and_execute_multi_deletion(
                    conn=conn,
                    query="DELETE FROM multiple_choice_market_answers WHERE contractId = ?",
                    ids=[market["id"] for market in markets]
                )
                
                answer_fields = [
                    "contractId", "createdTime", "fsUpdatedTime", "isOther", "answerIndex", 
                    "probability", "subsidyPool", "text", "totalLiquidity", "userId", 
                    "pool_NO", "pool_YES"
                ]
                
                prepare_and_execute_multi_upsert(
                    conn=conn,
                    query="INSERT OR REPLACE INTO multiple_choice_market_answers ({fields}) VALUES ({placeholders})",
                    fields=answer_fields,
                    data=[
                        {**answer,
                         "pool_NO": answer.get("pool", {}).get("NO", None),
                         "pool_YES": answer.get("pool", {}).get("YES", None)
                         } for market in markets for answer in market.get("answers", [])]
                )
            
            # Commit transaction
            conn.commit()
    
        except sqlite3.Error as e:
            print("Database error in upsert_multiple_choice_markets:", e)
            conn.rollback()  # Rollback transaction in case of error

        

    '''
    ########################################################
    ####                 CONTRACT METRICS               ####
    ########################################################
    '''
    def upsert_contract_metrics(self, contract_metrics: list[dict]):
            # Get database connection
            conn = self.get_conn()
            
            # Current UNIX epoch time for all contract_metrics in this batch
            current_time = int(time.time())
            
            # Begin transaction for better performance and data integrity
            conn.execute("BEGIN TRANSACTION;")

            try:

                # Base table
                base_fields = [
                    "contractId", "hasNoShares", "hasShares", "hasYesShares",
                    "invested", "loan", "maxSharesOutcome", "payout", 
                    "profit", "profitPercent", "userId", "userUsername", 
                    "userName", "lastBetTime", "retrievedTimestamp"
                ]
                prepare_and_execute_multi_upsert(
                    conn=conn,
                    query="INSERT OR REPLACE INTO contract_metrics ({fields}) VALUES ({placeholders})",
                    fields=base_fields,
                    data=[
                        {**metric, "retrievedTimestamp": current_time} for metric in contract_metrics]
                )

                
                # Handle nested tables (from and totalShares)
                # Delete entries
                prepare_and_execute_multi_deletion(
                    conn=conn,
                    query="DELETE FROM contract_metrics_from WHERE contractId = ? AND userId = ?",
                    ids=[(contract_metric["contractId"], contract_metric["userId"]) for contract_metric in contract_metrics]
                )
                
                from_fields = ["contractId", "userId", "period", "value", "profit", "invested", "prevValue", "profitPercent"]
                prepare_and_execute_multi_upsert(
                    conn=conn,
                    query="INSERT OR REPLACE INTO contract_metrics_from ({fields}) VALUES ({placeholders})",
                    fields=from_fields,
                    data=[
                        {**from_vals,
                         "contractId": contract_metric.get("contractId", None),
                         "userId": contract_metric.get("userId", None), 
                         "period": period} for contract_metric in contract_metrics for period, from_vals in contract_metric.get("from", {}).items()]
                )

                # Delete entries
                prepare_and_execute_multi_deletion(
                    conn=conn,
                    query="DELETE FROM contract_metrics_totalShares WHERE contractId = ? AND userId = ?",
                    ids=[(contract_metric["contractId"], contract_metric["userId"]) for contract_metric in contract_metrics]
                )
                
                total_shares_fields = ["contractId", "userId", "outcome", "numberOfShares"]
                prepare_and_execute_multi_upsert(
                    conn=conn,
                    query="INSERT OR REPLACE INTO contract_metrics_totalShares ({fields}) VALUES ({placeholders})",
                    fields=total_shares_fields,
                    data=[
                        {
                         "contractId": contract_metric.get("contractId", None),
                         "userId": contract_metric.get("userId", None),
                         "outcome": outcome,
                         "numberOfShares": numberOfShares
                         } for contract_metric in contract_metrics for outcome, numberOfShares in contract_metric.get("totalShares", {}).items()]
                )
            
                # Commit transaction
                conn.commit()
        
            except sqlite3.Error as e:
                print("Database error in upsert_contract_metrics:", e)
                conn.rollback()  # Rollback transaction in case of error

    '''
    ########################################################
    ####                      BETS                      ####
    ########################################################
    '''
    def upsert_bets(self, bets: list[dict]):
        # Get database connection
        conn = self.get_conn()
        
        # Current UNIX epoch time for all bets in this batch
        current_time = int(time.time())
        
        # Begin transaction for performance and data integrity
        conn.execute("BEGIN TRANSACTION;")

        try:
            # Fields for the bets base table
            bet_fields = [
                "id", "userId", "contractId", "isFilled", "amount", "probBefore",
                "isCancelled", "outcome", "shares", "limitProb", "loanAmount", 
                "orderAmount", "probAfter", "createdTime", "retrievedTimestamp"
            ]
            
            # Insert or replace into the bets base table
            prepare_and_execute_multi_upsert(
                conn=conn,
                query="INSERT OR REPLACE INTO bets ({fields}) VALUES ({placeholders})",
                fields=bet_fields,
                data=[{**bet, "retrievedTimestamp": current_time} for bet in bets]
            )
            
            # Handle nested tables (fees and fills)
            # Delete entries
            prepare_and_execute_multi_deletion(
                conn=conn,
                query="DELETE FROM bet_fees WHERE betId = ?",
                ids=[bet["id"] for bet in bets]
            )

            fee_fields = ["betId", "creatorFee", "liquidityFee", "platformFee"]
            prepare_and_execute_multi_upsert(
                conn=conn,
                query="INSERT OR REPLACE INTO bet_fees ({fields}) VALUES ({placeholders})",
                fields=fee_fields,
                data=[{**bet["fees"], "betId": bet["id"]} for bet in bets if "fees" in bet]
            )

            # Delete entries
            prepare_and_execute_multi_deletion(
                conn=conn,
                query="DELETE FROM bet_fills WHERE betId = ?",
                ids=[bet["id"] for bet in bets]
            )

            fill_fields = ["betId", "timestamp", "matchedBetId", "amount", "shares"]
            prepare_and_execute_multi_upsert(
                conn=conn,
                query="INSERT OR REPLACE INTO bet_fills ({fields}) VALUES ({placeholders})",
                fields=fill_fields,
                data=[{**fill, "betId": bet["id"]} for bet in bets for fill in bet.get("fills", [])]

            )
            
            # Commit transaction
            conn.commit()

        except sqlite3.Error as e:
            print("Database error in upsert_bets:", e)
            conn.rollback()  # Rollback transaction in case of error


class ManifoldDatabaseReader:
    def __init__(self, manifold_db):
        self.manifold_db = manifold_db
        self.manifold_db.get_conn().row_factory = self.dict_factory

    def dict_factory(self, cursor, row):
        """Row factory to produce dictionary results."""
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    def execute_query(self, query, params=None):
        """
        Execute a read query and return the results.

        :param query: The SQL query string.
        :param params: Any parameters for the query (optional).
        :return: The query results.
        """
        conn = self.manifold_db.get_conn()
        
        # Set row factory here so it returns dicts.
        conn.row_factory = self.dict_factory
        
        cursor = conn.cursor()
        cursor.execute(query, params or [])
        return cursor.fetchall()

class ManifoldDatabaseWriter:
    def __init__(self, manifold_db):
        self.manifold_db = manifold_db
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)  # Only one writer at a time for thread safety

    def queue_write_operation(self, function, *args, **kwargs):
        """
        Queue a write operation to the database.

        :param function: The function to execute (a write function from ManifoldDatabase class).
        :param args: Arguments for the function.
        :param kwargs: Keyword arguments for the function.
        :return: Future object representing the execution of the operation.
        """
        future = self.executor.submit(function, *args, **kwargs)
        return future