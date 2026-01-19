import { useState } from "react";

function App() {
  const [cardDeck, setCardDeck] = useState<Card[]>([]);

  return (
    <>
      <Header />

      <Footer />
    </>
  )
}



interface PlayerCardStack {
  isNPC: boolean; // If true, all cards except the table face-up cards will be invisible to the player
  tableFaceUpCards: Card[];
  tableFaceDownCards: Card[];
  cardsInHand: Card[]; // If all three arrays are empty, the player wins!
}
/**
 * Contains all the cards that a given player has.
 */
function PlayerCards({isNPC, tableFaceUpCards, tableFaceDownCards, cardsInHand}: PlayerCardStack) {

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
