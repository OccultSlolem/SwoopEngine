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

LOOP_DELAY = 1000 # ms
FORMAT = "%(message)s"
DEBUG_PRINTS = "-d" in sys.argv
logging.basicConfig(
    level="NOTSET" if DEBUG_PRINTS else "INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler(markup=True)]
)
log = logging.getLogger("rich")

ai_port = "8585"
ai_bridge_address = "127.0.0.1"
ai_bridge_port = "8000"
policy_id = "(PLACEHOLDER)"
current_game_id = ""

async def establish_connection():
    uri = f"ws://{ai_bridge_address}:{ai_bridge_port}/ws"
    websocket = await websockets.connect(uri, logger=log)
    TEST_STRING = "Hello Swoop!"
    TEST_MESSAGE = { "type": "TEST_CONNECTION", "payload": { "test_message": TEST_STRING } }
    await websocket.send(json.dumps(TEST_MESSAGE))

    response =json.loads(await websocket.recv())
    test_response = response.get("message")
    if test_response != TEST_STRING:
        log.critical("Failed to establish connection. Abort.")
        log.warning(f"Got: {test_response}")
        log.warning(f"Expected: {TEST_STRING}")
        sys.exit(-1)
    
    log.info("Connection to AI Bridge established!")
    return websocket

class GameStatus(str, Enum):
    IDLE = "IDLE"
    AWAITING_GAME_START = "AWAITING_GAME_START"
    AWAITING_TURN = "AWAITING_TURN"
    MY_TURN = "MY_TURN"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"

current_game_status: GameStatus = GameStatus.IDLE

async def connection_tick(connection: websockets.ClientConnection):
    global current_game_id, current_game_status
    log.debug("Tick")
    match current_game_status:
        case GameStatus.IDLE:
            message = { "type": "JOIN_ANY_GAME" }
            await connection.send(json.dumps(message))
            response = json.loads(await connection.recv())
            game_id = response.get("message")
            if not game_id or response["status"] != 200:
                log.critical("Failed to join/create game! Check ai_bridge logs. Abort.")
                os._exit(1)
            current_game_id = game_id
            log.info(f"Joined game {game_id}")
            log.info("Waiting for the game to start 😴")
            current_game_status = GameStatus.AWAITING_GAME_START
        
        case GameStatus.AWAITING_TURN:
            log.debug("Waiting for my turn 😴")
        case GameStatus.AWAITING_GAME_START:
            log.debug("Waiting for the game to start 😴")

        case GameStatus.MY_TURN:
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

    while True:
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
