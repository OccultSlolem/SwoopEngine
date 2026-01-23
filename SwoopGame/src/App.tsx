import { useRef, useState } from "react";

interface PlayerCardStack {
  // Key is the face down card, value is the corresponding face up card
  // Each one is set to null once played
  tableCards: Map<Card | null, Card | null>[];
  cardsInHand: Card[]; // If all three arrays are empty, the player wins!
}

// 1 = ace, 11 = jack, 12 = queen, 13 = king
// no jokers
type CardRank = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13;
type CardSuit = 'diamonds' | 'clubs' | 'spades' | 'hearts';
interface Card {
  suit: CardSuit;
  rank: CardRank;
}

interface AIConnection {
  address: string
  port: number
}

function App() {
  const [tableDeck, setTableDeck] = useState<Card[]>([]);
  const [liveCards, setLiveCards] = useState<Card[]>([]);
  const [playerCardStack, setPlayerCardStack] = useState<PlayerCardStack>({
    tableCards: [],
    cardsInHand: []
  });
  const [npcCardStacks, setNpcCardStacks] = useState<PlayerCardStack[]>([]);
  const [numNpcPlayers, setNumNpcPlayers] = useState(3);
  const [gameActive, setGameActive] = useState(false);
  const [aiBridgeWebsocket, setAiBridgeWebsocket] = useState<WebSocket | null>(null);
  const [aiConnections, setAiConnections] = useState<AIConnection[]>([]);
  const [playerIsAI, setPlayerIsAI] = useState(false);

  
  function shuffleCardDeck() {
    // Since there's no circumstance where we'll be generating a card deck outside
    // of generating a whole new game, let's just throw it in shuffleCardDeck mmkay?
    function generateCardDeck() {
      const suits: CardSuit[] = ['diamonds', 'clubs', 'spades', 'hearts'];
      const deck: Card[] = [];
      for (const suit of suits) {
        for (let rank = 1; rank <= 13; rank++) {
          deck.push({
            suit: suit,
            rank: rank as CardRank
          })
        }
      }
      return deck;
    }

    const fourDecks: Card[] = [];

    for (let i = 0; i < 4; i++) { // Shuffle four decks
      for (const card of generateCardDeck()) {
        fourDecks.push(card);
      }
    }

    // Fisher-Yates shuffle
    const shuffledDeck: Card[] = [];

    while (fourDecks.length) {
      const randomIndex = Math.floor(Math.random() * fourDecks.length)
      const element = fourDecks.splice(randomIndex, 1);
      shuffledDeck.push(element[0]);
    }

    return shuffledDeck
  }

  function initalizeGame() {
    setTableDeck([]);
    setLiveCards([]);

    const deck = shuffleCardDeck();
    if (numNpcPlayers < 2) {
      alert('Too few players! Abort.');
      return;
    }

    if (numNpcPlayers > 6) {
      alert('Too many players! Abort.');
      return;
    }

    const cardStacks: PlayerCardStack[] = [];

    function fail(message: string) {
      alert('Otherworldly forces have thrown the match. Abort.');
      console.error(message);
      return;
    }

    for (let i = 0; i <= numNpcPlayers; i++) {
      const cardStack: PlayerCardStack = {
        cardsInHand: [],
        tableCards: [],
      }
      // 1. distribute 14 cards to  cardsInHand
      // 2. Loop four times. Each time, pick a card to be face down (key) and a card to
      // be face up (value). Store these as a map in tableCards.

      // 1
      for (let j = 0; j < 14; j++) {
        const card = deck.pop();
        if (card) cardStack.cardsInHand.push(card);
        else { fail(`player ${i} cardsInHand`); return; };
      }

      // Sort cardsinHand by rank so they appear organized in the player's hand
      cardStack.cardsInHand.sort((a, b) => b.rank - a.rank);

      // 2
      for (let j = 0; j < 4; j++) {
        const downCard = deck.pop();
        const upCard = deck.pop()
        if (upCard && downCard) {
          const cardMap = new Map<Card, Card>();
          cardMap.set(downCard, upCard);
          cardStack.tableCards.push(cardMap);
        } else { fail(`player {i} tableCards`) }
      }

      cardStacks.push(cardStack);
    }

    setTableDeck(deck);
    console.log(cardStacks[0])
    setPlayerCardStack(cardStacks[0]);
    setNpcCardStacks(cardStacks.slice(1));
    setGameActive(true);
  }

  function clearGame() {
    setPlayerCardStack({
      tableCards: [],
      cardsInHand: [],
    });
    setTableDeck([]);
    setNpcCardStacks([]);
    setGameActive(false);
  }

  return (
    <>
      <Header 
        isGameActive={gameActive}
        clearGame={clearGame}
      />
        {
          gameActive ? 
            <Table
              playerCardStack={playerCardStack}
              npcCardStacks={npcCardStacks}
              liveCards={liveCards}
            /> : 
            <GameSettings 
              numNpcPlayers={numNpcPlayers}
              setNumNpcPlayers={setNumNpcPlayers} 
              startGame={initalizeGame}
              aiBridgeWebSocket={aiBridgeWebsocket}
              setAiBridgeWebsocket={setAiBridgeWebsocket}
              playerIsAi={playerIsAI}
              setPlayerIsAi={setPlayerIsAI}
            />
        }

      <Footer />
    </>
  )
}

function GameSettings({
  numNpcPlayers,
  setNumNpcPlayers,
  startGame,
  aiBridgeWebSocket,
  setAiBridgeWebsocket,
  playerIsAi,
  setPlayerIsAi
}: {
  numNpcPlayers: number,
  setNumNpcPlayers: (amount: number) => void,
  startGame: () => void,
  aiBridgeWebSocket: WebSocket | null,
  setAiBridgeWebsocket: (ws: WebSocket | null) => void,
  playerIsAi: boolean,
  setPlayerIsAi: (value: boolean) => void
}) {
  const [aiBridgeAddress, setAiBridgeAddress] = useState('127.0.0.1');
  const [aiBridgePort, setAiBridgePort] = useState(8000);

  type ConnectionStatus = 'IDLE' | 'SUCCESS' | 'LOADING' | 'FAILED';
  const [aiBridgeConnectionStatus, setAiBridgeConnectionStatus] = useState<ConnectionStatus>('IDLE');

  const numPlayersRef = useRef(3);

  function validateNumNpcPlayers() {
    if (numPlayersRef.current > 6) {
      alert('Too many NPC players! Max 6.')
      return;
    }

    if (numPlayersRef.current < 1) {
      alert('Too few NPC players! Minimum 1.')
      return;
    }

    console.log(`numplayers ${numPlayersRef.current}`)

    setNumNpcPlayers(numPlayersRef.current);
  }

  function connectAiBridge() {
    if (aiBridgePort < 0) {
      alert('AI Bridge port must be a positive number');
      return;
    }

    if (aiBridgeAddress === '') {
      alert('AI Bridge address is empty.');
      return;
    }

    setAiBridgeConnectionStatus('LOADING');
    const ws = new WebSocket(`ws://${aiBridgeAddress}:${aiBridgePort}/ws`);
    let connectionSuccessful = false;
    
    ws.addEventListener('open', (_) => {
      console.log('Connected to server');
      setAiBridgeConnectionStatus('SUCCESS');
      setAiBridgeWebsocket(ws);
      connectionSuccessful = true;
    });

    ws.addEventListener('close', (_) => {
      console.log('Disconnected from server');
      if (connectionSuccessful) setAiBridgeConnectionStatus('IDLE');
      setAiBridgeWebsocket(null);
    });

    ws.addEventListener('error', (e) => {
      console.error(`Connection error: ${e}`);
      setAiBridgeConnectionStatus('FAILED');
      setAiBridgeWebsocket(null);
    });

    // TODO: Actual message handlers. Will likely add in a higher-level function
    // in order to handle interactions with the AIs.
    ws.addEventListener('message', (e) => {
      console.log(`Received message: ${e.data}`);
    })
  }

  function disconnectAIBridge() {
    aiBridgeWebSocket?.close();
  }

  return (
    <div className="settings">
      <h4>Settings</h4>
      <h5>Number of NPC players: {(numNpcPlayers + (playerIsAi ? 1 : 0))}</h5>
      <label htmlFor="num-players">Number of NPC Players
        <input
          type="number"
          id="num-players"
          name="num-players"
          placeholder="Number of players"
          defaultValue={3}
          onChange={(e) => numPlayersRef.current = parseInt(e.target.value, 10)}
        />
        <button onClick={validateNumNpcPlayers}>
          Set
        </button>
      </label>

      <label htmlFor="ai-bridge-address">AI Bridge Address
        <input
          type="text"
          id="ai-bridge-address"
          name="ai-bridge-address"
          placeholder="AI Bridge Address"
          defaultValue={'127.0.0.1'}
          onChange={(e) => setAiBridgeAddress(e.target.value)}
        />
      </label>

      <label htmlFor="ai-bridge-port">AI Bridge Port
        <input
          type="number"
          id="ai-bridge-port"
          name="ai-bridge-port"
          placeholder="AI Bridge Port"
          defaultValue={8000}
          onChange={(e) => setAiBridgePort(parseInt(e.target.value, 10))}
        />
      </label>

      <label htmlFor="player-is-ai">AI-only game
        <input
          type="checkbox"
          id="player-is-ai"
          name="player-is-ai"
          onChange={(e) => setPlayerIsAi(e.target.checked)}
        ></input>
      </label>

      <div className="row-wrap">
        <p>AI Bridge Status: {aiBridgeConnectionStatus}</p>
        {
          aiBridgeWebSocket !== null ? (
            <button onClick={disconnectAIBridge}>Disconnect</button>
          ) : (
            <button onClick={connectAiBridge}>Connect</button>
          )
        }
      </div>

      {/* FIXME: Remove this test code */}
      {
        !!aiBridgeWebSocket && (
          <button onClick={(_) => aiBridgeWebSocket.send('Test')}>Test</button>
        )
      }

      <button onClick={startGame}>Initialize</button>
    </div>
  )
}

function Table(
  { playerCardStack, npcCardStacks, liveCards }:
  { playerCardStack: PlayerCardStack, npcCardStacks: PlayerCardStack[], liveCards: Card[] }
) {
  // In Swoop, if 4 cards of the same rank are played, it's counted as a trump card
  // This includes cards played by previous players, as long as they are the same rank
  // Hence why we want to know the last n cards of the same rank that were played
  const swoopableCards = (() => {
    if (liveCards.length === 0) return [];

    const toSwoopable: Card[] = [];
    const lastRank = liveCards[liveCards.length - 1].rank;

    for (let i = liveCards.length - 1; i >= 0; i--) {
      if (liveCards[i].rank !== lastRank || toSwoopable.length >= 4) {
        break;
      }
      toSwoopable.push(liveCards[i]);
    }
    return toSwoopable;
  })();

  function TableCardPair(
    { faceDownCard, faceUpCard, preventSelection }:
    { faceDownCard?: Card | null, faceUpCard?: Card | null, preventSelection?: boolean }
  ) {
    if (faceDownCard === null && faceUpCard === null) return (<></>);
    return (
      <div className="table-cards-column">
        {(faceDownCard?.rank) && (<Card card={faceDownCard} isFlipped preventSelection={preventSelection || false} />)}
        {(faceUpCard?.rank && (<Card card={faceUpCard} preventSelection={preventSelection || false} />))}
      </div>
    )
  }

  // This is used for face down cards which will always be flipped
  // Doesn't matter what this actually contains
  const dummyCard: Card = {
    rank: 1,
    suit: 'clubs'
  }

const totalCards = (() => {
  let total = playerCardStack.cardsInHand.length;
  for (const set of playerCardStack.tableCards) {
    set.forEach((card) => total += typeof(card) != 'undefined' ? 1 : 0)
  }
  return total;
})();

/**
 * Contains all the cards that a given player has.
 */
function PlayerCardsInHand() {

  if (totalCards === 0) {
    return (
      <h3>Congratulations!</h3>
    )
  }

  return (
    <div className="centered">
      <h2>Cards in your hand (Invisible to other players):</h2>
      {
        playerCardStack.cardsInHand.length > 0 ? (
          <div className="row-wrap">
            {
              playerCardStack.cardsInHand.map((card, index) => (
                <Card key={index} card={card} />
              ))
            }
          </div>
        ) : (
          <h3>No cards left in hand</h3>
        )
      }
      {/* Using row-wrap as its a convenient way to center the div */}
      <div className="row-wrap">
        <h5>Your Cards remaining: {totalCards}</h5>
      </div>
    </div>
  )
}

  return (
    <div className="table-container">
      <div className="row-wrap">
        {
          npcCardStacks.map((stack: PlayerCardStack, i) => (
            <div className="npc-container" key={i}>
              <h2>NPC Player {i + 1}</h2>
              <div className="row-wrap">
                <Card card={dummyCard} isFlipped />
                <h4>x{stack.cardsInHand.length} in hand</h4>
              </div>
              <div className="row-wrap">
                {
                  stack.tableCards.map((tableCardPair, v) => (
                    <TableCardPair
                      key={v}
                      faceDownCard={tableCardPair.keys().next().value ?? null}
                      faceUpCard={tableCardPair.values().next().value ?? null}
                      preventSelection
                    />
                  ))
                }
              </div>
            </div>
          ))
        }
      </div>

      {/* Render the live cards on the table */}
      {/* We render the last n cards of the same rank face up */}
      {/* The other cards don't matter except for if a player needs to pass, so  we */}
      {/* render them face down */}
      <div className="table-container border-red">
        <h2 className="centered">Table</h2>
        <div className="row-wrap">
          {
            (liveCards.length > 0) ? (
              <>
                <Card card={dummyCard} isFlipped />
                <h4>x {liveCards.length - swoopableCards.length} </h4>
                {
                  swoopableCards.map((card, i) => (
                    <Card key={i} card={card} />
                  ))
                }
              </>
            ) : (
              <h4>No live cards on table</h4>
            )
          }
        </div>
      </div>

      {/* Render the player's table cards */}
      <h2 className="centered">Your table cards (visible to all players):</h2>
      <div className="row-wrap">
        {
          playerCardStack.tableCards.map((pair, i) => (
            <TableCardPair
              key={i}
              faceDownCard={pair.keys().next().value ?? null}
              faceUpCard={pair.values().next().value ?? null}
            />
          ))
        }
      </div>

      <PlayerCardsInHand />
    </div>
  )
}

function Card(
  { card, isFlipped, preventSelection }: 
  { card: Card, isFlipped?: boolean, preventSelection?: boolean}
){
  const { rank, suit } = card;

  const color: 'black' | 'red' =  // automatically assign color based on suit
    (suit === 'diamonds' || suit === 'hearts') ? 'red' : 'black';
  
  const showTrumpCardColor = !isFlipped && (rank === 10 || rank === 11)

  if (isFlipped) return (<div className="flipped"></div>)
  
  return (
    <div 
      className={
        `card ${(!isFlipped && !preventSelection) ? 'card-selectable' : ''} card-${color}${showTrumpCardColor ? ' card-trump' : ''}`
      }
    >
      <h4>
        {
          suit === 'diamonds' ? '◆' :
          suit === 'clubs' ? '♧' :
          suit === 'spades' ? '♠' :
          '♥'
        }
      </h4>
      <h4>
        {
          rank === 1 ? 'A' :
          rank === 11 ? 'J' :
          rank === 12 ? 'Q' :
          rank === 13 ? 'K' :
          rank
        }
      </h4>
    </div>
  )
}


function Header(
  { isGameActive, clearGame }: 
  { isGameActive: boolean, clearGame: () => void }
) {
  return (
    <ul className="header">
      <h4>Swoop!</h4>
      {
        isGameActive && (
          <li>
            Clear Game
          </li>
        )
      }
    </ul>
  )
}

function Footer() {
  return (
    <></>
  )
}

export default App
