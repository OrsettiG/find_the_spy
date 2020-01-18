import os

class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or 'dev'
    
    # Set base directory and init db variables
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or "sqlite:///" + os.path.join(basedir, "game.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False