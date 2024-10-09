# config.py
import os
from dotenv import load_dotenv
# Cloudinary Configuration
import cloudinary
import cloudinary.uploader
import cloudinary.api

load_dotenv()
class Config:
    DATABASE_NAME = os.getenv('DATABASE_NAME')
    DATABASE_HOST = os.getenv('DATABASE_HOST')
    DATABASE_USER = os.getenv('DATABASE_USER')
    DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
    DATABASE_PORT = int(os.getenv('DATABASE_PORT'))
    

    SECRET_KEY = os.getenv('SECRET_KEY','default_secret_key')
    
    UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY','9zXMTqIIAc2fz6iC4XZzsIcSI9TgSlzom7TzpKgvGJM')


    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')

    @staticmethod
    def init_cloudinary():
        cloudinary.config(
            cloud_name=Config.CLOUDINARY_CLOUD_NAME,
            api_key=Config.CLOUDINARY_API_KEY,
            api_secret=Config.CLOUDINARY_API_SECRET
        )

    
    
