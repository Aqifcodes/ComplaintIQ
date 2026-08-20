import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = "change_this_to_a_long_random_secret_key"

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "../instance/complaintiq.db")

    # Absolute path to the project root SQLite database file
    DATABASE = os.path.abspath(os.path.join(BASE_DIR, "..", "complaintiq.db"))

    SQLALCHEMY_TRACK_MODIFICATIONS = False