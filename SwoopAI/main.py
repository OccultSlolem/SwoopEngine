import asyncio
import websockets
import logging
import json
import sys
import ast
import os
from enum import Enum
from rich import print
from rich.logging import RichHandler
from swooplib import GameState, SystemMessageType, ClientMessage, ClientMessageType
from card_player import simple_turn_processor

LOOP_DELAY = 1 # s
FORMAT = "%(message)s"
DEBUG_PRINTS = "-d" in sys.argv
logging.basicConfig(
    level="NOTSET" if DEBUG_PRINTS else "INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler(markup=True)]
)
log = logging.getLogger("rich")

class GameStatus(str, Enum):
    IDLE = "IDLE"
    AWAITING_GAME_START = "AWAITING_GAME_START"
    AWAITING_TURN = "AWAITING_TURN"
    MY_TURN = "MY_TURN"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"

ai_port: str = "8585"
ai_bridge_address: str = "127.0.0.1"
ai_bridge_port: str = "8000"
policy_id: str = "(PLACEHOLDER)"
current_game_id: str = ""
current_game_status: GameStatus = GameStatus.IDLE
current_game_state: GameState | None = None
# The player's card stack can be found at current_game_state.player_card_stacks[my_player_number]
my_player_number: int = -1 # Becomes a non-negative once connected to game
received_latest_game_state: bool = False
awaiting_response_from_last_turn: bool = False
requested_join_game = False

async def establish_connection():
    uri = f"ws://{ai_bridge_address}:{ai_bridge_port}/ws"
    websocket = await websockets.connect(uri, logger=log)
    TEST_STRING = "Hello Swoop!"
    TEST_MESSAGE = { "type": "TEST_CONNECTION", "payload": { "test_message": TEST_STRING } }
    await websocket.send(json.dumps(TEST_MESSAGE))

    response = json.loads(await websocket.recv())
    test_response = response.get("message")
    if test_response != TEST_STRING:
        log.critical("Failed to establish connection. Abort.")
        log.warning(f"Got: {test_response}")
        log.warning(f"Expected: {TEST_STRING}")
        sys.exit(-1)
    
    log.info("Connection to AI Bridge established!")
    return websocket

async def listen_for_messages(connection: websockets.ClientConnection):
    """Listens for messages from the server and updates the game state."""
    global current_game_status, current_game_state, received_latest_game_state, my_player_number, current_game_id, my_player_number, awaiting_response_from_last_turn
    try:
        async for message_raw in connection:
            message = json.loads(message_raw)
            
            # The server sometimes double-encodes messages. If so, the actual message is a string.
            if isinstance(message, str):
                message = json.loads(message)

            log.debug(f"Received message type: {type(message)}")

            if message.get("status") is not None:
                # FIXME
                # This is the old way of handling responses. Don't do anything.
                continue

            # Now 'message' is the actual content, whether it was nested or not.
            message_type = message.get("message_type")
            
            match message_type:
                case SystemMessageType.GAME_JOINED:
                    if message is None:
                        log.fatal("Something got horribly messed up while trying to join the game, WREKT")
                        os._exit(1)
                    # The GAME_JOINED message is inside the 'message' field of a status response
                    message_content = message.get("message")
                    try:
                        # The server sometimes sends a string representation of a dict with single quotes
                        payload = ast.literal_eval(message_content)
                    except (ValueError, SyntaxError, TypeError):
                        # Or it might already be a dict (if not double-encoded)
                        payload = message_content
                    game_id = payload.get("game_id")
                    player_number = payload.get("player_number")
                    if not game_id or player_number is None:
                        log.fatal("Didn't get the expected info back from the server.")
                        log.fatal(f"Received: {message}")
                        os._exit(1)
                    current_game_id = game_id
                    my_player_number = player_number
                    log.info(f"Joined game: {current_game_id} · Player number: {my_player_number}")
                case SystemMessageType.GAME_JOIN_FAILED:
                    log.fatal(f"Failed to join game :(")
                    os._exit(1)

                case SystemMessageType.GAME_STATUS:
                    payload = json.loads(message["message"])
                    current_game_state = GameState.model_validate(payload)
                    if current_game_state.game_active:
                        current_game_status = GameStatus.AWAITING_TURN if current_game_state.player_turn != my_player_number else GameStatus.MY_TURN
                        log.debug(f"🃏 My cards: {current_game_state.player_card_stacks[my_player_number]}")
                    else:
                        current_game_status = GameStatus.AWAITING_GAME_START
                    
                    
                    received_latest_game_state = True
                    awaiting_response_from_last_turn = False
                
                case SystemMessageType.GAME_COMPLETE:
                    current_game_status = GameStatus.COMPLETE
                case _:
                    log.warning(f"Received unknown message type: {message_type}")

    except websockets.exceptions.ConnectionClosed:
        log.error("Connection to server closed.")
        current_game_status = GameStatus.ERROR
    except Exception as e:
        log.error(f"Error processing message: {e}", exc_info=True)
        current_game_status = GameStatus.ERROR

EXPONENTIAL_BACKOFF_FACTOR = 2
MAX_BACKOFF_ATTEMPTS = 4
exponential_backoff_attempts: int = 0

async def connection_tick(connection: websockets.ClientConnection):
    global current_game_id, my_player_number, current_game_status, received_latest_game_state, exponential_backoff_attempts, awaiting_response_from_last_turn, requested_join_game
    log.debug("Tick")
    match current_game_status:
        case GameStatus.IDLE:
            if requested_join_game:
                log.warning("I asked to join a game but haven't received a response.")
                await asyncio.sleep(EXPONENTIAL_BACKOFF_FACTOR**exponential_backoff_attempts)
                if exponential_backoff_attempts >= MAX_BACKOFF_ATTEMPTS:
                    log.warning("Still haven't received a response after waiting a long time. Let's try again.")
                    exponential_backoff_attempts = 0
                else: return
            log.info("Looking for a game to join...")
            message = { "type": "JOIN_ANY_GAME" }
            await connection.send(json.dumps(message))
            # The listen_for_messages task will handle the response and state updates.
            # We just need to wait for the state to change.
        
        case GameStatus.AWAITING_TURN:
            if current_game_state: log.debug(f"Waiting for player {current_game_state.player_turn} 😴")
            await asyncio.sleep(LOOP_DELAY)
        case GameStatus.AWAITING_GAME_START:
            log.debug("Waiting for the game to start 😴")
            await asyncio.sleep(LOOP_DELAY)

        case GameStatus.MY_TURN:
            if not current_game_state:
                log.warning("Somehow it's my turn, but I haven't received the latest game state yet 🤔")
                log.warning("Waiting for a bit to see if it comes through.")
                await asyncio.sleep(2**exponential_backoff_attempts)
                exponential_backoff_attempts += 1
                if exponential_backoff_attempts >= MAX_BACKOFF_ATTEMPTS:
                    log.fatal("Didn't receive game state after waiting an inordinate amount of time. Abort.")
                    os._exit(1)
                    return
                return

            if not received_latest_game_state:
                await asyncio.sleep(LOOP_DELAY)
                return

            if awaiting_response_from_last_turn:
                log.warning("I haven't received a response from the server since I last tried to make a move.")
                log.warning("I'm gonna wait a bit to see if it responds")
                await asyncio.sleep(2**exponential_backoff_attempts)
                exponential_backoff_attempts += 1
                if exponential_backoff_attempts >= MAX_BACKOFF_ATTEMPTS:
                    log.warning("Didn't receive game state after waiting an inordinate amount of time.")
                    log.warning("I'm gonna try again.")
                    exponential_backoff_attempts = 0
                    awaiting_response_from_last_turn = False
                return
            
            play = simple_turn_processor(
                current_stack=current_game_state.player_card_stacks[my_player_number],
                live_cards=current_game_state.live_cards
            )

            action_request = {
                "game_id": current_game_id,
                "turn_request": play
            }

            log.info(f"🃏 Here's what I'm playing!\n{play}")

            exponential_backoff_attempts = 0
            received_latest_game_state = False
            awaiting_response_from_last_turn = True
            turn_message = ClientMessage(type=ClientMessageType.PROCESS_TURN, payload=action_request)
            await connection.send(message=turn_message.model_dump_json())

        case GameStatus.COMPLETE:
            rematch = input("Would you like to do another round? (Y/n) ").casefold() == "y"
            if not rematch:
                log.info("Goodbye!")
                os._exit(0)
            current_game_status = GameStatus.IDLE

        case GameStatus.ERROR:
            log.critical("Otherworldly forces have thrown the match. Abort.")
            log.info("Hint: If you don't see any useful console output here, try checking ai_bridge logs.")
            os._exit(1)

async def connection_loop(connection: websockets.ClientConnection):
    # Do something based on current_game_status
    # - Idle: Seek out a game to join
    # - Awaiting game start: No operation
    # - Awaiting Turn: No operation
    # - My turn: Evaluate the state of the table and process the best action accordingly
    # - Complete: Ask if we want to do another one
    # - Error: Exit
    # Sleep for a given number of ms
    # Repeat

    global current_game_status, current_game_id

    listen_task = asyncio.create_task(listen_for_messages(connection))

    while not listen_task.done():
        log.debug(f"Current game status: {current_game_status}")
        try:
            await connection_tick(connection)
        except Exception as e:
            log.error(e)
            log.error("Exception in listen_task")
            current_game_status = GameStatus.ERROR
        await asyncio.sleep(LOOP_DELAY / 1000) # asyncio defaults to seconds, so convert to ms
    

async def main(display_beginning: bool = True):
    global ai_port, ai_bridge_address, ai_bridge_port, policy_id, current_game_id
    def settings():
        return f"""\n----------\n[bold white]SETTINGS:[/bold white]
- [bold yellow]Game ID to join:[/bold yellow] {"None (Automatically seek out an open game)" if not current_game_id else current_game_id}
- [bold yellow]AI port:[/bold yellow] {ai_port} (will automatically pick the closest available port)
- [bold yellow]AI Bridge Address:[/bold yellow] {ai_bridge_address}
- [bold yellow]AI Bridge Port:[/bold yellow] {ai_bridge_port}
- [bold yellow]Policy ID:[/bold yellow] {policy_id}\n----------\n"""
   
    # ----
    
    if display_beginning: print(f"""[bold red]SwoopAI (c) Ethan Hanlon 2026 MIT License[/bold red]
{settings()}
[bold white]OPTIONS:[/bold white]
[bold green]1. Start
2. Manually specify AI port
3. Manually specify AI Bridge address
4. Manually specify AI Bridge port
5. Manually specify policy ID
6. Exit[/bold green]
""")
    else: print(settings())
    option = input("Option: ")
    match option:
        case "6":
            os._exit(0)
        case "5":
            policy_id = input("Enter policy ID: ")
        case "4":
            ai_bridge_port = input("Enter AI bridge port: ")
        case "3":
            ai_bridge_address = input("Enter AI bridge address: ")
        case "2":
            ai_port = input("Enter AI port: ")
        case "1":
            connection = await establish_connection()
            await connection_loop(connection)
        case _:
            log.error("Invalid option specified.")
    
    await main(display_beginning=False)
    

if __name__ == "__main__":
    asyncio.run(main())
