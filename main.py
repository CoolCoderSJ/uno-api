from pymongo import MongoClient
from flask import Flask, request, jsonify
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv
import random
import requests

load_dotenv()

app = Flask(__name__)
client = MongoClient(os.environ['MONGO_URI'])
db = client['uno']

cards = ["W", "W4"]
for color in ['R', 'Y', 'G', 'B']:
    for i in range(9):
        cards.append(color + "" + str(i + 1))
    
    for card in ["+2", "S", "R"]:
        cards.append(color + "" + card)


def internalRequest(method, path, scheme, host):
    return requests.request(method, f"{scheme}://{host}{path}").json()


@app.get('/api/players')
def getPlayers():
    players = db.players.find()
    return jsonify([{
        '_id': str(player['_id']),
        'name': player['name'],
        'hand': len(player['cards'])
    } for player in players])

@app.get('/api/state')
def gameState():
    game = db.game.find_one()
    if not game:
        c = cards.copy()
        c.remove("W")
        c.remove("W4")
        for card in c:
            if card[1] in ["+", "S", "R"]:
                c.remove(card)

        random.shuffle(c)
        card = c.pop()

        game = {
            "next_player": None,
            "direction": 1,
            "current_card": card,
            "_id": str(ObjectId()),
            "next_color": card[0]
        }
        db.game.insert_one(game)
        game = db.game.find_one()
    return game

@app.post('/api/join')
def joinGame():
    player = {
        "_id": str(ObjectId()),
        "name": request.json['name'],
        "cards": [random.choice(cards) for i in range(7)],
        "secret": str(ObjectId())
    }
    db.players.insert_one(player)
    return jsonify(player)

@app.post("/api/leave")
def leaveGame():
    try:
        db.players.find_one_and_delete({
            "_id": request.json['id'],
            "secret": request.json['secret']
        })
    except:
        return jsonify({"error": "Invalid player ID"})
    

    db.players.find_one_and_delete({
        "_id": request.json['id']
    })
    return jsonify({"success": True})

@app.post("/api/view_hand")
def viewHand():
    try:
        player = db.players.find_one({
            "_id": request.json['id'],
            "secret": request.json['secret']
        })
    except:
        return jsonify({"error": "Invalid player ID or secret"})
    
    return jsonify(player['cards'])

@app.post("/api/draw")
def drawCard():
    card = random.choice(cards)
    try:
        player = db.players.find_one({
            "_id": request.json['id'],
            "secret": request.json['secret']
        })
    except:
        return jsonify({"error": "Invalid player ID or secret"})

    nextPlayer = gameState()['next_player']
    if nextPlayer and nextPlayer != request.json['id']:
        return jsonify({"error": "Not your turn"})

    reverse = gameState()['direction'] == -1
    players = list(db.players.find())
    players = [player["_id"] for player in players]
    currentPlayer = players.index(request.json['id'])
    
    if reverse: 
        if currentPlayer > 0: currentPlayer -= 1
        else: currentPlayer = len(players) - 1
    else: 
        if currentPlayer < len(players) - 1: currentPlayer += 1
        else: currentPlayer = 0

    db.game.find_one_and_update({}, {
        "$set": {
            "next_player": players[currentPlayer]
        }
    })

    db.players.find_one_and_update({
            "_id": request.json['id'],
            "secret": request.json['secret']
        }, {
            "$push": {
                "cards": card
            }
        })

    return jsonify({
        "card": card
    })

@app.get("/api/uno")
def callUno():
    try:
        player = db.players.find_one({
            "_id": request.args['id']
    })
    except:
        return jsonify({"error": "Invalid player ID or secret"})

    if len(player['cards']) == 1:
        db.players.find_one_and_update({
            "_id": request.args['id']
        }, {
            "$set": {
                "uno": True
            }
        })
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Player does not have one card"})

@app.post("/api/play")
def playCard():
    if "card" not in request.json or "id" not in request.json or "secret" not in request.json:
        return jsonify({"error": "Missing parameters"})
    
    try:
        player = db.players.find_one({
            "_id": request.json['id'],
            "secret": request.json['secret']
        })
    except:
        return jsonify({"error": "Invalid player ID or secret"})

    card = request.json['card']
    if card not in cards:
        return jsonify({"error": "Invalid card"})
    if card not in db.players.find_one({"_id": request.json['id']})['cards']:
        return jsonify({"error": "Card not in hand"})
    
    nextPlayer = gameState()['next_player']
    if nextPlayer and nextPlayer != request.json['id']:
        return jsonify({"error": "Not your turn"})
    
    currentCard = gameState()['current_card']
    if card[0] == "W" and "color" not in request.json:
        return jsonify({"error": "Color must be declared to play wild card"})
    
    if card[0] != "W" and card[0] != gameState()['next_color'] and card[1:] != currentCard[1:]:
        return jsonify({"error": "Card cannot be played"})
    
    if card[0] == "W":
        color = request.json['color']
        if color not in ['R', 'Y', 'G', 'B']:
            return jsonify({"error": "Invalid color"})
    else:
        color = card[0]
    
    if (len(card)) == 1: card = "W "

    if card[1] == "R": reverse = True
    else: reverse = False
    db.game.find_one_and_update({}, {
        "$set": {
            "current_card": card,
            "next_color": color,
            "direction": -1 if reverse else 1
        }
    })

    db.players.find_one_and_update({
        "_id": request.json['id']
    }, {
        "$pull": {
            "cards": card.replace("W ", "W")
        }
    })

    players = list(db.players.find())

    for player in players:
        if len(player['cards']) == 1 and not player.get('uno', False):
            players.find_one_and_update({
                "_id": player['_id']
            }, {
                "$push": {
                    "cards": [random.choice(cards) for i in range(2)]
                }
            })

    players = [player["_id"] for player in players]
    currentPlayer = players.index(request.json['id'])
    skip = card[1] == "S" or card[1:] == "+2" or (card[1] == "R" and len(players) == 2)
    
    if reverse: 
        if currentPlayer > 0: currentPlayer -= (2 if skip else 1)
        else: currentPlayer = len(players) - (2 if skip else 1)

        if currentPlayer == -1: currentPlayer = len(players) - 1
    else: 
        if currentPlayer < len(players) - 1: currentPlayer += (2 if skip else 1)
        else: currentPlayer = (1 if skip else 0)

        if currentPlayer == len(players): currentPlayer = 0

    db.game.find_one_and_update({}, {
        "$set": {
            "next_player": players[currentPlayer],
            "next_player_name": db.players.find_one({"_id": players[currentPlayer]})['name']
        }
    })

    if card[1:] == "+2" or card == "W4":
        for i in range(int(card[-1])):
            card = random.choice(cards)
            db.players.find_one_and_update({
                "_id": players[currentPlayer]
            }, {
                "$push": {
                    "cards": card
                }
            })
    
    pCards = db.players.find_one({
        "_id": request.json['id']
    })['cards']
    if len(pCards) == 0:
        db.game.find_one_and_update({}, {
            "$set": {
                "winner": {
                    "id": request.json['id'],
                    "name": player['name'],
                },
                "next_player": None
            } 
        })
        for player in db.players.find():
            db.players.find_one_and_update({
                "_id": player['_id']
            }, {
                "$set": {
                    "cards": [random.choice(cards) for i in range(7)]
                }
            })
        return jsonify({"success": True, "winner": request.json['id']})
    
    return jsonify({"success": True})

app.run(host='0.0.0.0', port=8291, debug=True)