import asyncio
import websockets
import logging
import sys
import os
import json
from time import sleep
from enum import Enum
from rich import print
from rich.logging import RichHandler
from swooplib import GameState, SystemMessageType, PlayerCardStack
from card_player import simple_turn_processor

LOOP_DELAY = 1000 # ms
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

ai_port = "8585"
ai_bridge_address = "127.0.0.1"
ai_bridge_port = "8000"
policy_id = "(PLACEHOLDER)"
current_game_id = ""
current_game_status: GameStatus = GameStatus.IDLE
current_game_state: GameState | None = None
current_card_stack: PlayerCardStack | None = None

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
    global current_game_status, current_game_state
    try:
        async for message_raw in connection:
            message = json.loads(message_raw)
            log.debug(f"Received message: {message}")

            # This is a response to a request, not a system broadcast
            if "status" in message:
                if message["status"] != 200:
                    log.error(f"Received error from server: {message.get('message')}")
                else:
                    # This is a successful response to a request we sent.
                    # It might contain the game_id.
                    response_message = message.get("message")
                    if response_message and isinstance(response_message, str) and len(response_message) == 36: # Basic check for UUID
                        current_game_id = response_message
                        log.info(f"Joined game: {current_game_id}")
                continue

            # try:
            #     message.get("message_type")
            # except:
            #     print(F"ERROR: {type(message)}")
            #     print(f"ERROR: {type(json.loads(message))}")
            #     print(f"ERROR: {message}")
            message = json.loads(message) # Sometimes it won't load the first time. I don't know why.
            message_type = message.get("message_type")
            
            match message_type:
                case SystemMessageType.GAME_STATUS:
                    game_state_data = json.loads(message["message"])
                    current_game_state = GameState.model_validate(game_state_data)
                    if current_game_state.game_active:
                        current_game_status = GameStatus.AWAITING_TURN # Or MY_TURN
                    else:
                        current_game_status = GameStatus.AWAITING_GAME_START
                case SystemMessageType.GAME_COMPLETE:
                    current_game_status = GameStatus.COMPLETE
                case _:
                    log.warning(f"Received unknown message type: {message_type}")

    except websockets.exceptions.ConnectionClosed:
        log.warning("Connection to server closed.")
        current_game_status = GameStatus.ERROR
    except Exception as e:
        log.error(f"Error processing message: {e}", exc_info=True)
        current_game_status = GameStatus.ERROR

async def connection_tick(connection: websockets.ClientConnection):
    global current_game_id, current_game_status
    log.debug("Tick")
    match current_game_status:
        case GameStatus.IDLE:
            log.info("Looking for a game to join...")
            message = { "type": "JOIN_ANY_GAME" }
            await connection.send(json.dumps(message))
            # The listen_for_messages task will handle the response and state updates.
            # We just need to wait for the state to change.
        
        case GameStatus.AWAITING_TURN:
            log.debug("Waiting for my turn 😴")
            sleep(LOOP_DELAY)
        case GameStatus.AWAITING_GAME_START:
            log.debug("Waiting for the game to start 😴")
            sleep(LOOP_DELAY)

        case GameStatus.MY_TURN:
            # play = simple_turn_processor()
            pass # TODO

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
