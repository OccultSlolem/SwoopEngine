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
      alert('Too few players! Abort.')
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
  }



  return (
    <>
      <Header />
      <button onClick={initalizeGame}>Initialize</button>
        <PlayerCards stack={playerCardStack} />
      <Footer />
    </>
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
function PlayerCards({stack, isNPC}: { stack: PlayerCardStack, isNPC?: boolean }) {
  const [totalCards, setTotalCards] = useState(-1);

  useEffect(() => {
    console.log(stack)
    let total = stack.cardsInHand.length;
    for (const set of stack.tableCards) {
      set.forEach((card) => total += typeof(card) != 'undefined' ? 1 : 0)
    }

    setTotalCards(total);
  }, [stack]);

  if (totalCards === 0) {
    return (
      <h3>Congratulations!</h3>
    )
  }

  if (isNPC) {
    // We render all cards as flipped except for tableFaceUp cards
    return (
      <h3>TODO</h3>
    )
  }

  return (
    <>
      {
        stack.cardsInHand.length > 0 ? (
          <div className="row">
            {
              stack.cardsInHand.map((card, index) => (
                <Card key={index} suit={card.suit} value={card.value} isFlipped={card.isFlipped} />
              ))
            }
          </div>
        ) : (
          <h3>No cards left in hand</h3>
        )
      }
      {/* TODO: Render tableCards */}
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

  if (isFlipped) return (<div className="flipped"></div>)
  
  return (
    <div className={`card card-${color}`}>
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


function Header() {
  return (
    <ul className="header">
      <h4>Swoop!</h4>
    </ul>
  )
}

function Footer() {
  return (
    <></>
  )
}

export default App
