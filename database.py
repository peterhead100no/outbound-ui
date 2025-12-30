import psycopg2
from psycopg2 import sql, Error
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return None

def get_exotel_data():
    """Fetch specific columns from exotel_data table ordered by starttime"""
    try:
        connection = get_db_connection()
        if connection is None:
            return None
        
        query = """SELECT 
        \"call_sid\",
        \"To\", 
        \"From\",
        \"transcript\" , 
        \"summary\",
        \"priority\", 
        \"human_intervention\", 
        \"threat\",
        \"satisfaction\", 
        \"frustration\", 
        \"nuisance\", 
        \"repeated_complaint\", 
        \"pii_details\",
        \"status\", 
        CAST(\"duration\" AS INTEGER) AS \"duration\", 
        \"starttime\", 
        \"endtime\",
        \"recordingurl\"
        FROM public.exotel_data 
        WHERE \"recordingurl\" IS NOT NULL AND \"recordingurl\" != ''
        ORDER BY \"starttime\" DESC"""
        df = pd.read_sql_query(query, connection)
        connection.close()
        return df
    except Error as e:
        print(f"Error fetching data from database: {e}")
        return None
