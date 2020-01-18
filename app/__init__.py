from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.expression import func, select
from sqlalchemy.orm import exc
from flask_marshmallow import Marshmallow
from datetime import datetime
from config import Config
import os
import random

# Init App
app = Flask(__name__)

# Set static asset folder
app.static_folder = 'static'
app.config.from_object(Config)

# Init db
db = SQLAlchemy(app)

# Init marshmallow as ma - Maybe don't need this
ma = Marshmallow(app)

from app import views, models, options