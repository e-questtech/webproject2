import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Load environment variables from .env file
load_dotenv()

class Config:
    # Database configuration
    DATABASE_NAME = os.getenv('DATABASE_NAME')
    DATABASE_HOST = os.getenv('DATABASE_HOST')
    DATABASE_USER = os.getenv('DATABASE_USER')
    DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
    DATABASE_PORT = int(os.getenv('DATABASE_PORT', 3306))  # Defaulting to 3306 if not provided
    
    # Secret key for session management
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    
    # Cloudinary configuration
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')

    @staticmethod
    def init_cloudinary():
        # Check if Cloudinary credentials are missing
        if not Config.CLOUDINARY_CLOUD_NAME or not Config.CLOUDINARY_API_KEY or not Config.CLOUDINARY_API_SECRET:
            raise ValueError("Cloudinary credentials are not set in the environment variables")

        # Initialize Cloudinary with environment variables
        cloudinary.config(
            cloud_name=Config.CLOUDINARY_CLOUD_NAME,
            api_key=Config.CLOUDINARY_API_KEY,
            api_secret=Config.CLOUDINARY_API_SECRET
        )

    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = os.getenv('MAIL_PORT')
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS')
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL')
