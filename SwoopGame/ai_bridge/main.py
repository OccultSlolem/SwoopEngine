from typing import Optional, List, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from uuid import uuid4
from random import shuffle
from copy import deepcopy
from math import inf
import asyncio
import logging
import json
import os
from swooplib import (
    is_swoop,
    Card,
    CardPlay,
    CardSuit,
    GameState,
    PlayedFrom,
    PlayerCardStack,
    SystemMessage,
    SystemMessageType,
    TableCardPair,
    TurnActionRequest,
    TurnOutcome,
    ClientMessageType
)


log = logging.getLogger(__name__)

# --- Swoop logic

def initialize_card_deck(num_players: int):
    # 1. Generate 4 52-card decks (no jokers)
    # 2. Shuffle the deck
    # 3. Distribute the deck to the number of players specified
    # 4. Return the remaining cards in the deck and each player's decks

    # 1
    SUITS: List[CardSuit] = [suit for suit in CardSuit if suit != CardSuit.UNKNOWN]
    four_card_decks: List[Card] = []

    for _ in range(4):
        for suit in SUITS:
            for rank in range(1, 14):
                four_card_decks.append(Card(suit=suit, rank=rank))
    
    # 2

    shuffle(four_card_decks)
    shuffled_deck = four_card_decks # Use a more descriptive name
    
    # 3
    player_stacks: List[PlayerCardStack] = []
    for _ in range(num_players):
        stack = PlayerCardStack(
            table_cards=[],
            cards_in_hand=[]
        )

        # Distribute 14 cards to cards_in_hand
        for _ in range(14):
            card = shuffled_deck.pop()
            stack.cards_in_hand.append(card)
        
        # Distribute 4 pairs of cards to table_cards
        for pair_number in range(4):
            card_down = shuffled_deck.pop()
            card_up = shuffled_deck.pop()
            stack.table_cards.append(TableCardPair(pair_number=pair_number, face_down_card=card_down, face_up_card=card_up))
        
        player_stacks.append(stack)
    
    # 4
    return {
        "table_deck": shuffled_deck,
        "player_card_stacks": player_stacks
    }

class IncorrectPlayerAmountException(Exception):
    pass

class GameNotStartedException(Exception):
    pass

class GameAlreadyStartedException(Exception):
    pass

class IllegalMoveException(Exception):
    pass

class BadArgumentException(Exception):
    pass

class Game:
    """Represents a single game instance"""
    def __init__(self, playing_to: int, max_players: int, game_id: str):
        self.game_id = game_id
        self.players: List[WebSocket] = []
        self.game_state = GameState(
            table_deck=[],
            live_cards=[],
            player_card_stacks=[],
            player_points=[],
            player_turn=0,
            max_players=max_players,
            playing_to=playing_to,
            turn_actions=[],
            game_active=False
        )
        log.info(f"GAME CREATED: {game_id}")
            
    
    async def add_player(self, websocket: WebSocket) -> int:
        """Join a game and return the player number of who joined"""
        if (self.game_state.game_active):
            raise GameAlreadyStartedException("This game has already started, can't add new players")
        log.info(f"Player added to game {self.game_id}: {websocket.client.host}:{websocket.client.port}") # type: ignore
        self.players.append(websocket)
        joined_game_message = SystemMessage(
            message_type=SystemMessageType.GAME_JOINED, 
            message=str({
                "game_id": self.game_id,
                "player_number": len(self.players) - 1
            })
        )
        await websocket.send_json(joined_game_message.model_dump_json())
        await self.broadcast_game_state()
        return len(self.players) - 1
    
    async def remove_player(self, websocket: WebSocket):
        if websocket not in self.players:
            raise BadArgumentException("Player not in game")
        log.info(f"Player removed from game {self.game_id}: {websocket.client.host}:{websocket.client.port}") # type: ignore
        self.players.remove(websocket)
        await self.broadcast_game_state()
    
    async def start_game(self):
        num_players = len(self.players)

        if num_players < 2 or num_players > 6:
            raise IncorrectPlayerAmountException("Games must have between 2 and 6 players.")

        deck = initialize_card_deck(num_players)
        self.game_state.player_card_stacks = deck["player_card_stacks"]
        self.game_state.table_deck = deck["table_deck"]
        self.game_state.game_active = True
        for _ in range(num_players):
            self.game_state.player_points.append(0)
        log.info(f"GAME STARTED: {self.game_id}")
        await self.broadcast_game_state()
    
    async def abort_game(self, message: Optional[str]):
        """Disconnect all clients and save game to disk"""
        log.critical(f"ABORTING GAME {self.game_id}: {message}")
        for player in self.players: await player.close()
        self.save_game_to_disk()

    
    def process_turn(self, player: int, action_request: TurnActionRequest) -> TurnOutcome:
        # 1. Parse what the player did
        # 2. If the player passed, they must pick up all cards on table
        # 3. Ensure that the action was legal
        # 4. Check if the move resulted in a win (last card played)
        # 5. If no win, check if a swoop occured and clear live_cards if so.
        # 6. Return the turn outcome.

        if not self.game_state.game_active:
            raise GameNotStartedException("The game has not started.")
        
        if player != self.game_state.player_turn:
            raise IllegalMoveException("It's not your turn!")
        
        if player < 0:
            raise BadArgumentException("Attempted to play on a negative player.")
        
        if player >= len(self.game_state.player_card_stacks):
            raise IncorrectPlayerAmountException("Attempted to act on a nonexistent player.")
        
        player_stack = self.game_state.player_card_stacks[player]
        if len(action_request.cards_played) == 0:
            # The player passed, they must pick up all cards on table
            player_stack.cards_in_hand.extend(self.game_state.live_cards)
            self.game_state.live_cards = []
            return TurnOutcome.PICKED_UP_CARDS_ON_TABLE
        
        top_live_rank = self.game_state.live_cards[0].rank if len(self.game_state.live_cards) > 0 else inf

        # Check if the player put down an upside down table card
        if action_request.upside_down_card_played is not None:
            # This is a blind play. The player doesn't know what card they are playing.
            pair = next(p for p in player_stack.table_cards if p.pair_number == action_request.upside_down_card_played)

            if not pair.face_down_card:
                print("***")
                print(f"Player's table cards: {player_stack.table_cards}")
                raise IllegalMoveException("This pair doesn't seem to have an upside down card")
            
            card_played = pair.face_down_card
            if card_played.rank > top_live_rank: 
                player_stack.cards_in_hand.extend(self.game_state.live_cards)
                self.game_state.live_cards = []
                return TurnOutcome.PICKED_UP_CARDS_ON_TABLE
            
            # The player can only play this one card. We'll send it through the processing system like any other.
            action_request.cards_played = [CardPlay(card=pair.face_down_card, played_from=PlayedFrom.UPSIDE_DOWN_TABLE_CARD)]


        # Validate that the cards played exist in the player's stack
        for play in action_request.cards_played:
            card_played = play.card
            played_from = play.played_from

            if played_from == PlayedFrom.CARDS_IN_HAND:
                if card_played not in player_stack.cards_in_hand:
                    raise IllegalMoveException(f"Card {card_played} not in player's hand.")
            elif played_from == PlayedFrom.RIGHTSIDE_UP_TABLE_CARD:
                if not any(d.face_up_card == card_played for d in player_stack.table_cards):
                    raise IllegalMoveException(f"Card {card_played} not on player's face-up table cards.")
            elif played_from == PlayedFrom.UPSIDE_DOWN_TABLE_CARD:
                # This shouldn't be necessary since it's picked right out of the player's hand, but we'll validate it just in case
                if not any(d.face_down_card == card_played for d in player_stack.table_cards):
                    raise IllegalMoveException(f"Card {card_played} not on player's face-down table cards.")
        
        # Validate that all cards played have the same rank
        first_card_rank = action_request.cards_played[0].card.rank
        if not all(play.card.rank == first_card_rank for play in action_request.cards_played):
            raise IllegalMoveException("All cards played in a single turn must have the same rank.")

        # Validate that the rank played is legal
        # Swoop cards (10 and jack) are always legal to play
        if first_card_rank > top_live_rank and (first_card_rank != 10 and first_card_rank != 11):
            raise IllegalMoveException("Card played has higher rank than top of live cards.")

        # The move is legal, so remove the cards from the player's stack
        for play in action_request.cards_played:
            card_played = play.card
            played_from = play.played_from

            if played_from == PlayedFrom.CARDS_IN_HAND:
                player_stack.cards_in_hand.remove(card_played)
            elif played_from == PlayedFrom.RIGHTSIDE_UP_TABLE_CARD:
                for i, table_card_pair in enumerate(player_stack.table_cards):
                    if table_card_pair.face_up_card == card_played:
                        player_stack.table_cards[i].face_up_card = None
                        break
            elif played_from == PlayedFrom.UPSIDE_DOWN_TABLE_CARD:
             for i, table_card_pair in enumerate(player_stack.table_cards):
                if table_card_pair.face_down_card == card_played:
                    player_stack.table_cards[i].face_down_card = None
                    break
        
        swoop_check = is_swoop(first_card_rank, len(action_request.cards_played), self.game_state.live_cards)
        
        # Add played cards to the live_cards pile
        played_cards = [play.card for play in action_request.cards_played]
        self.game_state.live_cards = played_cards + self.game_state.live_cards

        # Check for victory condition
        if (
            len(player_stack.cards_in_hand) == 0 and
            all(card_pair.face_up_card is None for card_pair in player_stack.table_cards) and
            all(card_pair.face_down_card is None for card_pair in player_stack.table_cards)
        ):
            asyncio.run(self.process_round_completion())
            return TurnOutcome.VICTORY
        elif swoop_check:
            self.game_state.live_cards = []
            return TurnOutcome.SWOOP

        return TurnOutcome.REGULAR_TURN
    
    async def broadcast_all(self, message: SystemMessage):
        # These next two lines exist primarily to facilitate unit testing in mockless setups
        if len(self.players) == 0: return
        if (all(player is None for player in self.players)): return
        for player in self.players:
            await player.send_json(message.model_dump_json())
    
    async def broadcast_game_state(self):
        message = SystemMessage(message_type=SystemMessageType.GAME_STATUS, message=self.game_state.model_dump_json())
        await self.broadcast_all(message)
    
    def sanitize_table_cards(self, table_cards: List[TableCardPair]) -> List[TableCardPair]:
        sanitized_pairs: List[TableCardPair] = []
        for pair in table_cards:
            sanitized_pair = TableCardPair(
                pair_number=pair.pair_number,
                face_down_card=Card(suit=CardSuit.UNKNOWN, rank=0) if pair.face_down_card else None,
                face_up_card=pair.face_up_card
            )
            sanitized_pairs.append(sanitized_pair)
        
        return sanitized_pairs

    def sanitize_other_player_cards(self, other_card_stack: PlayerCardStack) -> PlayerCardStack:
        """
        Sanitizes another player's card stack for a given player's viewing. Use this before transmitting to each player
        the state of the table.
        """
        sanitized_stack = PlayerCardStack(
            table_cards=self.sanitize_table_cards(other_card_stack.table_cards),
            cards_in_hand=[]
        )
        for _ in range(len(other_card_stack.cards_in_hand)):
            sanitized_stack.cards_in_hand.append(Card(suit=CardSuit.UNKNOWN, rank=0))

        return sanitized_stack
    
    def sanitize_my_cards(self, my_card_stack: PlayerCardStack) -> PlayerCardStack:
        """
        Sanitizes a player's card stack for their own viewing. Use this before transmitting to each player
        the state of their cards.
        """
        sanitized_stack = PlayerCardStack(
            table_cards=self.sanitize_table_cards(my_card_stack.table_cards),
            cards_in_hand=my_card_stack.cards_in_hand
        )

        return sanitized_stack
    
    async def broadcast_sanitized_game_state(self):
        # Each player should not be able to view the cards in hand of other players
        # They also should not be able to see any face down table cards, including their own
        # Create a set of player stacks for each player

        num_players = len(self.players)

        for viewing_player_idx in range(num_players):
            player_websocket = self.players[viewing_player_idx]
            if not player_websocket:
                # FIXME: More graceful error handling
                await self.abort_game(f"A player disconnected, the websockets are all out of order. Abort the game.")
                return
            
            sanitized_state = deepcopy(self.game_state)
            sanitized_state.player_card_stacks = []
            for stack_player_idx in range(num_players):
                if viewing_player_idx == stack_player_idx:
                    sanitized_state.player_card_stacks.append(self.sanitize_my_cards(self.game_state.player_card_stacks[stack_player_idx]))
                else:
                    sanitized_state.player_card_stacks.append(self.sanitize_other_player_cards(self.game_state.player_card_stacks[stack_player_idx]))
                
            
            message = SystemMessage(message_type=SystemMessageType.GAME_STATUS, message=sanitized_state.model_dump_json())
            await player_websocket.send_json(message.model_dump_json())

    async def process_round_completion(self):
        # Assign points based on how many cards people have left
        # Number cards are worth 5 points, face cards are worth 10, trump cards (10/jack) are worth 25
        # End the game if any player has a point value >= self.game_state.playing_to
        def point_value_of_card(card: Card) -> int:
            if card.rank < 10: return 5
            if card.rank == 10 or card.rank == 11: return 25
            if card.rank == 12 or card.rank == 13: return 10
            raise Exception("Illegal card rank!")

        for i in range(0, len(self.game_state.player_card_stacks)):
            stack = self.game_state.player_card_stacks[i]
            points_this_round = 0
            for card in stack.cards_in_hand: points_this_round += point_value_of_card(card)
            for pair in stack.table_cards:
                if pair.face_up_card: points_this_round += point_value_of_card(pair.face_up_card)
                if pair.face_down_card: points_this_round += point_value_of_card(pair.face_down_card)
            
            self.game_state.player_points[i] += points_this_round
        
        if any(points >= self.game_state.playing_to for points in self.game_state.player_points):
            self.game_state.game_active = False
            message = SystemMessage(message_type=SystemMessageType.GAME_COMPLETE, message="")
            await self.broadcast_all(message)
            for connection in self.players: 
                if connection: await connection.close()
            return

        message = SystemMessage(message_type=SystemMessageType.ROUND_COMPLETE, message=self.game_state.model_dump_json())
        await self.broadcast_all(message)

    
    def save_game_to_disk(self):
        """Saves the final game state and turn history to a JSON file"""
        # Create a directory to store the game logs if it doesn't exist.
        LOG_DIR = "game_logs"
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)

        file_path = os.path.join(LOG_DIR, f"game-{self.game_id[0:8]}-log.json")
        with open(file_path, "w") as f:
            f.write(self.game_state.model_dump_json(indent=2))
        print(f"Game {self.game_id} saved to {file_path}")


class GameManager:
    """Singleton class that manages all active game sessions"""
    def __init__(self):
        # The str represents a unique game ID
        self.active_games: Dict[str, Game] = {}
    
    async def create_game(self, playing_to: int, max_players: int, host: WebSocket):
        game_id = str(uuid4())
        game_state = Game(playing_to, max_players, game_id)
        await game_state.add_player(host)
        self.active_games[game_id] = game_state
        return game_id
    
    async def join_game_by_id(self, player: WebSocket, game_id: str) -> int:
        """Join a game by its ID and return the player number. Will return -1 if it failed."""
        if game_id not in self.active_games:
            log.warning(f"Player attempted to join game {game_id} but was not found.")
            return -1

        game = self.active_games[game_id]
        # Check if there is room for the additional player
        num_players = len(game.players)
        if num_players + 1 > game.game_state.max_players:
            return -1
        player_number = await game.add_player(player)
        return player_number
    
    async def join_any_game(self, player: WebSocket) -> tuple[str, int]:
        requester_player_number = 0

        # If there are no active games, create a new game
        if len(self.active_games) == 0:
            return (await self.create_game(playing_to=300, max_players=6, host=player), requester_player_number)
        
        # Join any game that has capacity
        for game in self.active_games.values():
            num_players = len(game.players)
            max_players = game.game_state.max_players
            if num_players + 1 > max_players: continue
            requester_player_number = await game.add_player(player)
            return game.game_id, requester_player_number

        # If all games are at capacity, create a new game
        return (await self.create_game(playing_to=300, max_players=6, host=player), requester_player_number)



# --- FastAPI Application

app = FastAPI()
game_manager = GameManager()

@app.get("/")
def read_root():
    return { "Hello": "World" }

@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            try:
                return_value = await sort_message(data, websocket, game_manager)
                await websocket.send_json(return_value.model_dump())
            except Exception as e:
                log.error("Error processing message", exc_info=e)
                await websocket.send_json({ "status": 500, "message": "Error" })
    except WebSocketDisconnect:
        log.info(f"Client disconnected: {websocket.client.host}:{websocket.client.port}") # type: ignore
        #TODO: Cleanup logic, especially if a client disconnects mid-game.

class MessageStatus(BaseModel):
    status: int
    message: str

async def sort_message(response: Dict, websocket: WebSocket, game_manager: GameManager) -> MessageStatus:
    """
    Takes a WebSocket message and "sorts" it to the relevant processing function.
    Structuring it this way reduces indentation.
    """
    message_type = response.get("type")
    if not message_type:
        return MessageStatus(status=400, message="No message type specified")
    
    payload_data = response.get("payload", {})
    
    match message_type:
        case ClientMessageType.TEST_CONNECTION:
            return MessageStatus( status=200, message=payload_data.get("test_message", "Connection successful"))

        case ClientMessageType.CREATE_GAME:
            playing_to = payload_data.get('playing_to', 300)
            max_players = payload_data.get('max_players', 6)
            
            game_id = await game_manager.create_game(playing_to, max_players, host=websocket)
            return MessageStatus(status=200, message=game_id)
        
        case ClientMessageType.JOIN_GAME_BY_ID:
            game_id = payload_data.get('game_id')
            if not game_id:
                raise BadArgumentException("No game ID in payload")
            
            player_number = await game_manager.join_game_by_id(websocket, game_id)
            response = {
                "player_number": player_number
            }
            status_number = 200 if player_number > -1 else 400
            return MessageStatus(status=status_number, message=json.dumps(response))

        case ClientMessageType.JOIN_ANY_GAME:
            game_id, player_number = await game_manager.join_any_game(websocket)
            response = {
                "game_id": game_id,
                "player_number": player_number
            }
            return MessageStatus(status=200, message=json.dumps(response))
        
        case ClientMessageType.PROCESS_TURN:
            print(f"Processing a turn: {payload_data}")
            turn_request = payload_data.get("turn_request")
            cards_played = turn_request.get("cards_played")
            upside_down_card_played = turn_request.get("upside_down_card_played", None)
            game_id = payload_data.get("game_id")
            if cards_played is None:
                return MessageStatus(status=400, message="No cards_played in payload")
            
            if game_id is None:
                return MessageStatus(status=400, message="No game ID specified")
            
            if game_id not in game_manager.active_games:
                log.warning(game_id)
                log.warning(game_manager.active_games.get(game_id))
                return MessageStatus(status=400, message="Game does not exist or is not active")
            
            game = game_manager.active_games[game_id]
            player_number = game.players.index(websocket)
            if player_number < 0:
                return MessageStatus(status=400, message="You are not in this game")
            
            try:
                action_request = TurnActionRequest(cards_played=cards_played, upside_down_card_played=upside_down_card_played)
            except Exception as e:
                return MessageStatus(status=400, message=f"Invalid turn request format: {e}")
            
            try:
                print(f"Current player: {game.game_state.player_turn}")
                table_rank = 999 if not game.game_state.live_cards else game.game_state.live_cards[0].rank
                print(f"Current table rank: {table_rank}")
                outcome = game.process_turn(player_number, action_request)
                print(f"Outcome: {outcome}")
                if outcome != TurnOutcome.VICTORY and outcome != TurnOutcome.SWOOP:
                    # Move to next turn
                    wrap_turns_around = game.game_state.player_turn == len(game.players) - 1
                    game.game_state.player_turn = game.game_state.player_turn + 1 if not wrap_turns_around else 0
                
                print("---")
                
                await game.broadcast_sanitized_game_state()
                     
                return MessageStatus(status=200, message=f"Turn processed with outcome: {outcome.value}")
            except Exception as e:
                log.error(e)
                return MessageStatus(status=500, message="Failed to process turn")
        
        case _:
            return MessageStatus(status=400, message=F"Unknown message type: {message_type}")

@app.post("/start-games")
async def start_all_games():
    """Start all games that have at least 2 players"""
    started_games = []
    for game_id, game in game_manager.active_games.items():
        if len(game.players) >= 2 and not game.game_state.game_active:
            try:
                await game.start_game()
                started_games.append(game_id)
            except Exception as e:
                log.error(f"Failed to start game {game_id}: {e}")
    
    return MessageStatus(status=200, message=f"Started {len(started_games)} games")
