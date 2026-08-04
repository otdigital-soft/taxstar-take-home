import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me-32chars!!")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me-32chars!!")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRY_HOURS = 24
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.getenv("MONGO_DB", "taxstar")
    # Hardcoded local key is fine for this exercise (per spec).
    FERNET_KEY = os.getenv(
        "FERNET_KEY",
        "S8DIhcB79PuHAhHDnWt-e-m6vIiUUF3MW1ldwFOlr3s=",
    )
