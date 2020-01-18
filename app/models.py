from app import app, db, func
from app.options import secrets
# from app import *

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
    name = db.Column(db.String(50), nullable=False)
    name_date = db.Column(db.String(100), unique=True, nullable=False)
    rounds = db.relationship('Round', secondary='rounds_games', backref="game",lazy='dynamic')
    
    
# Round class/model
class Round(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    players = db.relationship('Player', secondary='players_rounds', backref="round", lazy='select')
    secret = db.relationship('Secret', backref="round", lazy='select', uselist=False)
    spy_count = db.Column(db.Integer, nullable=False)
        
    
# # Player Class/Model
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True) 
    name = db.Column(db.String(50), nullable=False)
    win_count = db.Column(db.Integer, nullable=False)
    
    
# # Secret Class/Model
class Secret(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey('round.id'))
    category = db.Column(db.String(50), nullable=False)
    value = db.Column(db.String(100), unique=True, nullable=False)
    
    
# Helpers

####### Game Functions #######
# Generate new Game
def new_Game(game_name, name_date):
    g = Game(name=game_name, name_date=name_date)
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


def add_from_last_round(last_round, r):
    for player in last_round.players:
            r.players.append(player)

####### Player Functions #######
# Generate new Player
def new_Player(name, win_count):
    if not name == "" or name == " ":
        p = Player(name=name, win_count=win_count)
        return p
    else: pass

# Select spies from current round Player list
def pick_spies(r):
    spies = Player.query.join(Round.players).order_by(func.random()).filter(Round.id == r.id).limit(r.spy_count).all()
    return spies


def player_total(lst, num_players):
    for item in lst:
        num_players += 1
    return num_players

def add_Players(player_names, r):
    for name in player_names:
        p = new_Player(name, 0)
        db.session.add(p)
        r.players.append(p)

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
        for secret in used_secrets:
            secret.round_id = None
            db.session.add(secret)
    db.session.commit()
    
# Add Secrets from list
def add_secret_from_list(lst):
    for category in lst:
            for value in lst[category]:
                if not Secret.query.filter_by(category=category, value=value).first():
                    s = Secret(category=category, value=value)
                    db.session.add(s)
    db.session.commit()

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

def get_game_name():
    g = db.session.query(Game).join(Game, Round.game).first()
    return g.name


