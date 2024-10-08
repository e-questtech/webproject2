# config.py
import os
from dotenv import load_dotenv

load_dotenv()
class Config:
    DATABASE_NAME = os.getenv('DATABASE_NAME')
    DATABASE_HOST = os.getenv('DATABASE_HOST')
    DATABASE_USER = os.getenv('DATABASE_USER')
    DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
    DATABASE_PORT = os.getenv('DATABASE_PORT')
    

    SECRET_KEY = os.getenv('SECRET_KEY','default_secret_key')
    
    UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY','9zXMTqIIAc2fz6iC4XZzsIcSI9TgSlzom7TzpKgvGJM')
    WTF_CSRF_ENABLED = True
