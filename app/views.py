from app import app, request, jsonify, render_template, datetime, random, db, exc
from app.models import *

session = db.session

@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST' and request.form["btn"] == "New Game":
        
        # Load Variables with form data
        try:
            player_names = request.form["playerNames"].split(', ')
            name_date = request.form["gameName"] + f" {datetime.today()}"
            game_name = request.form["gameName"]
            num_players = len(player_names)
            secret_category = request.form["secretSelect"]
        except:
            return render_template('template.html')
            
        # Drop all the old data from the last game (testing only)
        # db.drop_all()
        # db.create_all()
        
        # Create a new game and add it to the session
        try:
            g = new_Game(game_name, name_date)
            session.add(g)
        except:
            session.rollback()
            session.invalidate()
            return render_template('template.html')
        
        # Create a new round with appropriate spy_count and add it to the session
        try:
            r = new_Round(num_players)
            session.add(r)
        except:
            session.rollback()
            session.invalidate()
            return render_template('template.html')
        
        
        # Add the new round to the game
        g.rounds.append(r)
        
        # Create a player for each name in the form data and add them to the round
        try:
            add_Players(player_names, r)
        except exc.UnmappedInstanceError:
            session.rollback()
            session.close()
            return render_template('template.html')
        
        # print(r.players)
        # Delete any rows used in the last game
        delete_used_secrets()
        
        # Add any new secrets to the db
        add_secret_from_list(secrets)
        
        # Randomize and set the secret
        r.secret = random_secret(secret_category)
        
        # Commit session to db
        try:
            session.commit()
        except Exception as e:
            pass
        # Generate list of players and secrets
        players = generate_player_secrets(r)
        gameName = g.name
        
        # Pass players to template.html
        return render_template('template.html', players=players, gameName=gameName)
    elif request.method == "POST" and request.form["btn"] == "Add Players":
        
        # Load Vars with form data
        player_names = request.form["playerNames"].split(', ')
        num_players = len(player_names)
        
        # Get current round from db  order_by(Round.id.desc()).first()
        r = session.query(Round).order_by(Round.id.desc()).first()
        
        # Add the number of players in form data to players in current round
        try: 
            total_players = player_total(r.players, num_players)
        except AttributeError:
            return render_template('template.html')
        
        # Update the round spy_count with correct number for the players
        r.spy_count = count_spies(total_players)
        
        # Add new players to the session/round
        try:
            add_Players(player_names, r)
            # Commit session to db
            session.commit()
        except exc.UnmappedInstanceError:
            session.rollback()
            pass
            
        # Generate list of players and secrets (secret stays the same if players are added part way through round, but spies will change).
        players = generate_player_secrets(r)
        
        gameName = get_game_name()
        
        # Pass player list to template.html
        return render_template('template.html', players=players, gameName=gameName)
    elif request.method == "POST" and request.form["btn"] == "New Round":
        
        # Load vars with form and previous round data for easy handling
        player_names = request.form["playerNames"].split(', ')
        # try:
        last_round = Round.query.order_by(Round.id.desc()).first()
        # except:
        
        try:
            num_players = len(player_names) + len(last_round.players)
        except AttributeError:
            return render_template('template.html')
        
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
        add_from_last_round(last_round, r)
        
        # Check if there are any new players to add to the round
        if len(player_names) > 0 and not player_names[0] == '' or player_names[0] == ' ':
            try:
                add_Players(player_names, r)
            except exc.UnmappedInstanceError:
                session.rollback()
                session.invalidate()
                return render_template('template.html')
        
        # Commit session to db
        session.commit()
        
        # Generate list of players and secrets 
        players = generate_player_secrets(r)
         
        gameName = get_game_name()
        
        return render_template('template.html', players=players, gameName=gameName)
    return render_template('template.html')

@app.route('/reset123411', methods=['GET'])
def reset():
    db.drop_all()
    db.create_all()
    return "db reset"




# @app.route('/', methods=['POST'])
# def add_players():
#     if request.method == "POST" and request.form["add-btn"] == "Add Players":
        
#         # Load Vars with form data
#         player_names = request.form["playerNames"].split(', ')
#         print(player_names)
#         num_players = len(player_names)
        
#         # Get current round from db
#         r = Round.query.order_by(Round.id.desc()).first()
#         print(r)
        
#         # Add the number of players in form data to players in current round 
#         total_players = player_total(r.players, num_players)
#         print(total_players)
        
#         # Update the round spy_count with correct number for the players
#         r.spy_count = count_spies(total_players)
        
#         # Add new players to the session/round
#         for name in player_names:
#             p = new_Player(name, 0)
#             session.add(p)
#             r.players.append(p)
            
#         print(r.players)
        
#         # Commit session to db
#         session.commit()
        
#         # Generate list of players and secrets (secret stays the same if players are added part way through round, but spies will change).
#         players = generate_player_secrets(r)
        
#         # Pass player list to template.html
#         return render_template('template.html', players=players)
#     return render_template('template.html')
   
   
# @app.route('/', methods=['POST', 'GET'])
# def new_round():   
#     if request.method == "POST" and request.form["new-btn"] == "New Round":
        
#         # Load vars with form and previous round data for easy handling
#         player_names = request.form["playerNames"].split(', ')
#         last_round = Round.query.order_by(Round.id.desc()).first()
#         num_players = len(player_names) + len(last_round.players)
#         secret_category = request.form["secretSelect"]
        
#         # Create a new round with appropriate spy_count and secret and add it to the session
#         r = new_Round(num_players)
#         session.add(r)
        
#         # Load round with randomized secret - will not repeat an already used secret
#         r.secret = random_secret(secret_category)
        
#         # Get current Game, add it to the session and add Round to current it
#         g = Game.query.order_by(Game.id.desc()).first()
#         session.add(g)
#         g.rounds.append(r)
        
#         # Add last round players to new round
#         for player in last_round.players:
#             r.players.append(player)
        
#         # Check if there are any new players to add to the round
#         if len(player_names) > 0 and not player_names[0] == '' or player_names[0] == ' ':
#             for name in player_names:
#                 p = Player(name=name, win_count=0)
#                 session.add(p)
#                 r.players.append(p)
        
#         # Commit session to db
#         session.commit()
        
#         # Generate list of players and secrets 
#         players = generate_player_secrets(r)
        
#         return render_template('template.html', players=players)
#     return render_template('template.html')