import logging
import sys
from rich import print
from rich.logging import RichHandler

FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler(markup=True)]
)
log = logging.getLogger("rich")
DEBUG_PRINTS = "-d" in sys.argv

def main():
    print("""[bold red]SwoopAI (c) Ethan Hanlon 2026 MIT License[/bold red]

[bold white]DEFAULT SETTINGS:[/bold white]
- [bold yellow]AI port:[/bold yellow] 8585 (will automatically pick the closest available port)
- [bold yellow]AI Bridge Address:[/bold yellow] 127.0.0.1
- [bold yellow]AI Bridge Port:[/bold yellow] 8000
- [bold yellow]Policy ID:[/bold yellow] (PLACEHOLDER)
          
[bold white]OPTIONS:[/bold white]
[bold green]1. Manually specify AI port
2. Manually specify AI Bridge address
3. Manually specify AI Bridge 
4. Manually specify policy ID
5. Exit[/bold green]
""")
    option = input("Option: ")

if __name__ == "__main__":
    main()
