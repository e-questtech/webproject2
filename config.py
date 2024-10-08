# config.py
import os
from dotenv import load_dotenv

load_dotenv()
class Config:
    DATABASE_NAME = os.getenv('DATABASE_NAME')
    DATABASE_HOST = os.getenv('DATABASE_HOST')
    DATABASE_USER = os.getenv('DATABASE_USER')
    DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
    DATABASE_PORT = int(os.getenv('DATABASE_PORT'))
    

    SECRET_KEY = os.getenv('SECRET_KEY','default_secret_key')
    
    UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY','9zXMTqIIAc2fz6iC4XZzsIcSI9TgSlzom7TzpKgvGJM')
    
    IMAGEKIT_PRIVATE_KEY=os.getenv('IMAGEKIT_PRIVATE_KEY'),
    IMAGEKIT_PUBLIC_KEY=os.getenv('IMAGEKIT_PUBLIC_KEY'),
    IMAGEKIT_URL_ENDPOINT=os.getenv('IMAGEKIT_URL_ENDPOINT')
    
    
