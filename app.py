from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import func, select
from flask_marshmallow import Marshmallow
from datetime import datetime
import os
import random
from options import options

# Init App
app = Flask(__name__)

# Set base directory for app files
basedir = os.path.abspath(os.path.dirname(__file__))

# Set static asset folder
app.static_folder = 'static'

# Database path config
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "game.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

game_engine = create_engine("sqlite:///" + os.path.join(basedir, "game.db"))

Session = sessionmaker(bind=game_engine)



# Init db
db = SQLAlchemy(app)

# Init marshmallow as ma - Maybe don't need this
ma = Marshmallow(app)

# Many to Many Table for Players and Rounds Class
players_rounds = db.Table('players_rounds',
                          db.Column('player_id', db.Integer, db.ForeignKey('player.id')),
                          db.Column('round_id', db.Integer, db.ForeignKey('round.id')))

# Many to Many Table for Rounds and Games Class
rounds_games = db.Table('rounds_games',
                        db.Column('round_id', db.Integer, db.ForeignKey('round.id')),
                        db.Column('game_id', db.Integer, db.ForeignKey('game.id')))

# Classes/Models
# Game class/model
class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    rounds = db.relationship('Round', secondary='rounds_games', backref="game", lazy='select')
    
    
# Round class/model
class Round(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    players = db.relationship('Player', secondary='players_rounds', backref="round", lazy='select')
    secret = db.relationship('Secret', backref="round", lazy='select', uselist=False)
    spy_count = db.Column(db.Integer)
        
    
# # Player Class/Model
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True) 
    name = db.Column(db.String(50))
    win_count = db.Column(db.Integer)
    
    
# # Secret Class/Model
class Secret(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey('round.id'))
    category = db.Column(db.String(50))
    value = db.Column(db.String(100), unique=True)
    

# Player Schema for returning JSON - Maybe don't need this
class PlayerSchema(ma.Schema):
    class Meta:
        fields = ('name', 'secret', 'win_count')
        
    
      

# Index Route with Game interface
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST' and request.form["btn"] == "New Game":
        session = Session()
        # Load Variables with form data
        player_names = request.form["playerNames"].split(', ')
        game_name = request.form["gameName"] + f" {datetime.today()}"
        num_players = len(player_names)
        secret_category = request.form["secretSelect"]
        
        # Drop all the old data from the last game (testing only)
        # db.drop_all()
        # db.create_all()
        
        # Create a new game and add it to the session
        g = new_Game(game_name)
        session.add(g)
        
        # Create a new round with appropriate spy_count and add it to the session
        r = new_Round(num_players)
        session.add(r)
        
        # Add the new round to the game
        g.rounds.append(r)
        
        # Create a player for each name in the form data and add them to the round
        for name in player_names:
            p = new_Player(name, 0)
            session.add(p)
            r.players.append(p)
        
        # Delete any rows used in the last game
        # delete_used_secrets()
        
        # Add any new secrets to the db
        for category in options:
            for value in options[category]:
                if not Secret.query.filter_by(category=category, value=value).first():
                    s = Secret(category=category, value=value)
                    session.add(s)
        
        # Randomize and set the secret
        r.secret = random_secret(secret_category)
        
        # Generate list of players and secrets
        players = generate_player_secrets(r)
        
        # Commit session to db
        try:
            session.commit()
        except expression as e:
            session.flush()
        finally:
            session.close()
        
        
        # Pass players to template.html
        return render_template('template.html', players=players)
    elif request.method == "POST" and request.form["btn"] == "Add Players":
        
        # Load Vars with form data
        player_names = request.form["playerNames"].split(', ')
        num_players = len(player_names)
        
        # Get current round from db
        r = Round.query.order_by(Round.id.desc()).first()
        
        # Add the number of players in form data to players in current round 
        total_players = player_total(r.players, num_players)
        
        # Update the round spy_count with correct number for the players
        r.spy_count = count_spies(total_players)
        
        # Add new players to the session/round
        for name in player_names:
            p = new_Player(name, 0)
            session.add(p)
            r.players.append(p)
        
        # Commit session to db
        session.commit()
        
        # Generate list of players and secrets (secret stays the same if players are added part way through round, but spies will change).
        players = generate_player_secrets(r)
        
        # Pass player list to template.html
        return render_template('template.html', players=players)
    elif request.method == "POST" and request.form["btn"] == "New Round":
        
        # Load vars with form and previous round data for easy handling
        player_names = request.form["playerNames"].split(', ')
        last_round = Round.query.order_by(Round.id.desc()).first()
        num_players = len(player_names) + len(last_round.players)
        secret_category = request.form["secretSelect"]
        
        # Create a new round with appropriate spy_count and secret and add it to the session
        r = new_Round(num_players)
        session.add(r)
        
        # Load round with randomized secret - will not repeat an already used secret
        r.secret = random_secret(secret_category)
        
        # Get current Game, add it to the session and add Round to current it
        g = Game.query.order_by(Game.id.desc()).first()
        session.add(g)
        g.rounds.append(r)
        
        # Add last round players to new round
        for player in last_round.players:
            r.players.append(player)
        
        # Check if there are any new players to add to the round
        if len(player_names) > 0 and not player_names[0] == '' or player_names[0] == ' ':
            for name in player_names:
                p = Player(name=name, win_count=0)
                session.add(p)
                r.players.append(p)
        
        # Commit session to db
        session.commit()
        
        # Generate list of players and secrets 
        players = generate_player_secrets(r)
        
        return render_template('template.html', players=players)
    return render_template('template.html')

# Helpers

####### Game Functions #######
# Generate new Game
def new_Game(game_name):
    g = Game(name=game_name)
    return g


####### Round Functions #######
# Generate new Round
def new_Round(num_players):
    spy_count = count_spies(num_players)
    r = Round(spy_count=spy_count)
    return r


# Count players and assign appropriate number of spies
def count_spies(total_players):
    if total_players <= 10:
        spy_count = 1
    elif total_players <= 16:
        spy_count = 2
    elif total_players > 16:
        spy_count = 3
    return spy_count

####### Player Functions #######
# Generate new Player
def new_Player(name, win_count):
    if not name == "" or name == " ":
        p = Player(name=name, win_count=win_count)
        return p
    else: pass

# Select spies from current round Player list
def pick_spies(r):
    spies = Player.query.join(Round.players).order_by(func.random()).filter(Round.id == r.id).slice(0, r.spy_count).all()
    return spies


def player_total(lst, num_players):
    for item in lst:
        num_players += 1
    return num_players

####### Secret Functions #######
# Add any new secrets to db
def new_Secret(category, value):
    if not Secret.query.filter_by(category=category, value=value).first():
        s = Secret(category=category, value=value)
        return s
    else: pass

# Generate a random secret 
def random_secret(secret_category):
    return Secret.query.order_by(func.random()).filter_by(round_id=None, category=secret_category).first()

# Delete used secrets from db
def delete_used_secrets():
    used_secrets = Secret.query.filter(Secret.round_id != None)
    if not used_secrets == None:
        used_secrets.delete()

####### Output Functions #######

# Create a list of id matched lists
def id_matched_nested_list(lst_1, lst_2, id_match_value, no_match_value):
    lst_3 = []
    for item in lst_1:
        if id_match(lst_2, item.id):
            p = [item.id, item.name, id_match_value]
            lst_3.append(p)
        else:
            p = [item.id, item.name, no_match_value]
            lst_3.append(p)
    return lst_3

# Generate list of lists containing a player and secret
def generate_player_secrets(r):
    # Get the players in the current round
    r_plrs = r.players
    
    # Randomly generate player list of of length spy_count to be spies
    spies = pick_spies(r)
    
    # Get secret from round
    secret = r.secret.value
    
    # List with lists of player-secret pairs
    players = id_matched_nested_list(r_plrs, spies, "Spy", secret)
    
    return players

# Loop over a list and compare every id in the list with the target id. Return true only on a match
def id_match(lst, id):
    for item in lst:
        if item.id == id:
            return True
    return False 
# Init Schemas
# player_schema = PlayerSchema(strict=True)
# players_schema = PlayerSchema(many=True, strict=True)


# cli commands for dev
@app.cli.command("reset_db")
def reset_data():
    db.drop_all()
    db.create_all()
    
    print("db reset successful")
    
@app.cli.command("test_db")
def test_data():
    # Reset db
    db.drop_all()
    db.create_all()
    
    print("db reset successful")
    
    # Create table data variables
    # Two test games
    g_1 = Game(name="Test Game One")
    # g_2 = Game(name="Test Game Two")
    
    # Test Rounds for game 1
    r_1_g_1 = Round(spy_count=1)
    r_2_g_1 = Round(spy_count=1)
    # r_3_g_1 = Round(spy_count=1)
    # r_4_g_1 = Round(spy_count=1)
    
    # Test Rounds for game 2
    # r_1_g_2 = Round(spy_count=1)
    # r_2_g_2 = Round(spy_count=1)
    # r_3_g_2 = Round(spy_count=1)
    # r_4_g_2 = Round(spy_count=1)
    # Players
    gavin = Player(name="Gavin", win_count=0)
    reyah = Player(name="Reyah", win_count=0)
    steven = Player(name="Steven", win_count=0)
    daniel = Player(name="Daniel", win_count=0)
    
    
    
    # Add table data
    session.add(g_1)
    # session.add(g_2)
    session.add(gavin)
    session.add(reyah)
    session.add(steven)
    session.add(daniel)
    session.add(r_1_g_1)
    session.add(r_2_g_1)
  
    for category in options:
        for value in options[category]:
            s = Secret(category=category, value=value)
            print(s.category, s.value)
            session.add(s)
    
    # Append g_1 data to tables
    g_1.rounds.append(r_1_g_1)
    # g_1.rounds.append(r_2_g_1)
    # g_1.rounds.append(r_3_g_1)
    # g_1.rounds.append(r_4_g_1)
    r_1_g_1.players.append(gavin)
    r_1_g_1.players.append(reyah)
    r_1_g_1.players.append(steven)
    r_1_g_1.players.append(daniel)
    r_1_g_1.secret = Secret.query.order_by(func.random()).filter_by(round_id=None).first()
    
    # Append g_2 data to tables
    g_1.rounds.append(r_2_g_1)
    r_2_g_1.players.append(gavin)
    r_2_g_1.players.append(reyah)
    r_2_g_1.players.append(steven)
    r_2_g_1.players.append(daniel)
    r_2_g_1.secret = Secret.query.order_by(func.random()).filter_by(round_id=None).first()
    
    # Commit session to db
    session.commit()
    
    print("Successfully added test data to db")

# Run Server
if __name__ == "__main__":
    app.run(debug=True)
    