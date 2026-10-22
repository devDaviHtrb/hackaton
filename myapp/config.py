from dotenv import load_dotenv
from secrets import token_hex
from cryptography.fernet import Fernet
from os import getenv

load_dotenv()

class Config:
    # Flask standardization uppercase config attributes

    #======================= EMAIL =======================
    CORPORATION_EMAIL =     getenv("CORPORATION_EMAIL", "")
    CORPORATION_PASSWORD =  getenv("CORPORATION_PASSWORD", "")
    #=====================================================

    #==================== GOOGLE AUTH ====================
    GOOGLE_CLIENT_ID =      getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_SECRECT =        getenv("GOOGLE_SECRECT", "")
    GOOGLE_PROJECT_ID =     getenv("GOOGLE_PROJECT_ID", "")
    GOOGLE_REDIRECT_URIS =  getenv("GOOGLE_REDIRECT_URIS", "")
    REDIRECT_URI =          getenv("REDIRECT_URI", "")
    #=====================================================

    #=============== DEMOGRAFIX (Genderize) ===============
    DEMOGRAFIX_API_KEY =    getenv("DEMOGRAFIX_API_KEY", "")
    #======================================================

    #=============== OPENALEX ===============
    OPENALEX_API_KEY =      getenv("OPENALEX_API_KEY", "")
    #========================================
    
    #============== FLASK & SOCKETIO ==============
    SOCKETIO_ASYNC_MODE =   getenv("SOCKETIO_ASYNC_MODE", "threading")
    DEBUG =                 getenv("DEBUG", "True").lower() in ("true", "1", "t")
    #==============================================

    #========================= DATABASES =========================
    SQLALCHEMY_DATABASE_URI = getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///hackathon.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CLOUDINARY_CLOUD_NAME =   getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY =      getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET =   getenv("CLOUDINARY_API_SECRET", "")
    #=============================================================

    #=============== KEYS ===============
    SECRET_KEY =    getenv("SECRET_KEY", token_hex(32))
    raw_fernet =    getenv("FERNET_KEY")
    FERNET_KEY =    raw_fernet.encode() if raw_fernet else Fernet.generate_key()
    #====================================

    #=============== LOCAL SERVER ===============
    FLASK_ENV = getenv("FLASK_ENV", "development")
    HOST =      getenv("HOST", "0.0.0.0")
    PORT =      int(getenv("PORT", 5000))
    #============================================

    #===================== FLASK CACHE =====================
    CACHE_TYPE =            getenv("CACHE_TYPE", "SimpleCache")
    CACHE_REDIS_URL =       getenv("CACHE_REDIS_URL", None)
    CACHE_DEFAULT_TIMEOUT = int(getenv("CACHE_DEFAULT_TIMEOUT", 300))
    #=======================================================