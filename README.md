# Uno API
Play UNO...via API!

Uno API is a RESTful API that allows you to play UNO with your friends. You can play all the normal functions of UNO, just via API.

## How it works
Detailed information is available at the [API Documentation](https://bump.sh/coolcodersj/doc/uno), but here's a quick overview:
1. Join a game. A game is automatically created if it doesn't exist when you run the join endpoint. Otherwise, you're added to the end of the queue for an existing game. 
2. When you join, you're given a player ID, secret, and 7 cards. Use the player ID and secret to authenticate your moves.
3. Play your turn. You can play a card or draw a card.
    a. If you play a card, it must match the color or number of the card on the top of the discard pile.
    b. There are **no house rules**. This means you cannot stack cards, play right after drawing, etc.
4. When you have one card left, you must call UNO. If you don't call UNO before the next player goes, you will be given 2 cards automatically.
5. The game continues until someone has no cards left. That person is the winner! At this point, the game state resets- everyone is given 7 cards and anyone can play a card to start a new game.