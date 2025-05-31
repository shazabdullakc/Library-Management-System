import os
import sqlite3

def config():
    # Define the database file path
    db_path = os.path.join(os.path.dirname(__file__), 'library.db')
    return {'database': db_path}