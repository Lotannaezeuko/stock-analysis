from dotenv import load_dotenv
import os
import psycopg2
import streamlit as st

load_dotenv()

def get_connection():
    db_url = os.getenv("DATABASE_URL") or st.secrets["DATABASE_URL"]
    return psycopg2.connect(db_url)