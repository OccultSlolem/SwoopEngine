import { useEffect, useState } from "react";

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

  
  function shuffleCardDeck() {
    // Since there's no circumstance where we'll be generating a card deck outside
    // of generating a whole new game, let's just throw it in shuffleCardDeck mmkay?
    function generateCardDeck() {
      const suits: CardSuit[] = ['diamonds', 'clubs', 'spades', 'hearts'];
      const deck: Card[] = [];
      for (const suit of suits) {
        for (let value = 1; value <= 13; value++) {
          deck.push({
            suit,
            value: value as CardValue
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

    for (let i = 0; i < numNpcPlayers; i++) {
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
      cardStack.cardsInHand.sort((a, b) => b.value - a.value);

      // 2
      for (let j = 0; j < 4; j++) {
        const downCard = deck.pop();
        if (downCard) {
          downCard.isFlipped = true;
        } else { fail(`player ${i} tableCardsDown`); return; };

        const upCard = deck.pop()
        if (upCard) {
          const cardMap = new Map<Card, Card>();
          cardMap.set(downCard, upCard);
          cardStack.tableCards.push(cardMap);
        }
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
            <Game
              playerCardStack={playerCardStack}
              npcCardStacks={npcCardStacks}
            /> : 
            <GameSettings setNumNpcPlayers={setNumNpcPlayers} startGame={initalizeGame} />
        }
      <Footer />
    </>
  )
}

function GameSettings({
  setNumNpcPlayers,
  startGame
}: {
  setNumNpcPlayers: (amount: number) => void,
  startGame: () => void
}) {
  return (
    <div className="settings">
      <h4>Settings</h4>
      <label htmlFor="num-players">Number of Players</label>
      <input
        type="number"
        id="num-players"
        name="num-players"
        placeholder="Number of players"
        defaultValue={3}
        onChange={(e) => setNumNpcPlayers(Number(e.target.value))}
      />
      <button onClick={startGame}>Initialize</button>
    </div>
  )
}

function Game(
  { playerCardStack, npcCardStacks }:
  { playerCardStack: PlayerCardStack, npcCardStacks: PlayerCardStack[] }
) {
  return (
    <>
      <Table playerCardStack={playerCardStack} npcCardStacks={npcCardStacks} />
      <PlayerCardsInHand playerCardStack={playerCardStack} />
    </>
  )
}

function Table(
  { playerCardStack, npcCardStacks }:
  { playerCardStack: PlayerCardStack, npcCardStacks: PlayerCardStack[] }
) {
  return (
    <div className="table-container">
      {
        npcCardStacks.map((stack: PlayerCardStack, i) => (
          <div className="npc-wrapper" key={i}>
            <h4>placeholder</h4>
          </div>
        ))
      }

      {/* Render the player's table cards */}
      <div className="table-container row-wrap">
        <h4>Your table cards (visible to all players)</h4>
        {
          playerCardStack.tableCards.map((pair, i) => {
            const faceDown = pair.keys().next();
            const faceUp = pair.values().next();

            if (faceDown === null && faceUp === null) return (<></>);
            return (
              <div className="table-cards-column" key={i}>
                {(faceDown.value) && (<Card suit={faceDown.value.suit} value={faceDown.value.value} isFlipped />)}
                {(faceUp.value && (<Card suit={faceUp.value.suit} value={faceUp.value.value} />))}
              </div>
            )
          })
        }
      </div>
    </div>
  )
}

interface PlayerCardStack {
  // Key is the face down card, value is the corresponding face up card
  // Each one is set to null once played
  tableCards: Map<Card | null, Card | null>[];
  cardsInHand: Card[]; // If all three arrays are empty, the player wins!
}
/**
 * Contains all the cards that a given player has.
 */
function PlayerCardsInHand({ playerCardStack }: { playerCardStack: PlayerCardStack }) {
  const [totalCards, setTotalCards] = useState(-1);

  useEffect(() => {
    let total = playerCardStack.cardsInHand.length;
    for (const set of playerCardStack.tableCards) {
      set.forEach((card) => total += typeof(card) != 'undefined' ? 1 : 0)
    }

    setTotalCards(total);
  }, [playerCardStack]);

  if (totalCards === 0) {
    return (
      <h3>Congratulations!</h3>
    )
  }

  return (
    <>
      <h4>Cards in your hand (Invisible to other players)</h4>
      {
        playerCardStack.cardsInHand.length > 0 ? (
          <div className="row-wrap">
            {
              playerCardStack.cardsInHand.map((card, index) => (
                <Card key={index} suit={card.suit} value={card.value} isFlipped={card.isFlipped} />
              ))
            }
          </div>
        ) : (
          <h3>No cards left in hand</h3>
        )
      }
      {/* Using row-wrap as its a convenient way to center the div */}
      <div className="row-wrap">
        <h5>Cards remaining: {totalCards}</h5>
      </div>
    </>
  )
}

// 1 = ace, 11 = jack, 12 = queen, 13 = king
// no jokers
type CardValue = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13;
type CardSuit = 'diamonds' | 'clubs' | 'spades' | 'hearts';
interface Card {
  suit: CardSuit;
  value: CardValue;
  isFlipped?: boolean;
}
function Card({ suit, value, isFlipped }: Card) {
  const color: 'black' | 'red' =  // automatically assign color based on suit
    (suit === 'diamonds' || suit === 'hearts') ? 'red' : 'black';
  
  const showTrumpCardColor = !isFlipped && (value === 10 || value === 11)

  if (isFlipped) return (<div className="flipped"></div>)
  
  return (
    <div className={`card card-${color}${showTrumpCardColor ? ' card-trump' : ''}`}>
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
          value === 1 ? 'A' :
          value === 11 ? 'J' :
          value === 12 ? 'Q' :
          value === 13 ? 'K' :
          value
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
