# SwoopEngine

I originally had the idea for this way back in 2023 but then kinda forgot about it.
Now I'm picking it back up again.

## The Project

The idea is to create a robot with an AI that is capable of playing Swoop. This is of
course a bit of an undertaking, so there's a few steps:

- Build an interface to play Swoop for development purposes
- Build and train an AI to play the shit out of Swoop
- Create a camera system that can recognize cards
- Design and build some sort of robot that can somehow move all the cards where they need to go.

One step at a time though 😅

## The Game

*Note: there are a few different ways people play Swoop. This is the way my family does 
it.*

**Swoop** is a card game where players compete to minimize points by playing all the
cards from their hands. Like Uno, you win a round by being the first to play all your
cards. At the end of each round, players score points based on how many cards they had
left - like golf, fewer points is better. The game continues until a player reaches a set
point threshold, at which point the player with the lowest score wins. Cards are
distributed from a stack composed of four 52-card sets. Jokers are not used.

Every player starts with:

- 14 cards in their hand (invisible to other players)
- 4 face-down cards in front of them (invisible to all players including themselves)
- 4 face-up cards, one on top of each face-down card (visible to all players)

Players take turns playing cards from their hand, face-up cards, or face-down cards. Each
player must play a card lower than or equal to the player behind them did. They can play
multiple cards as long as they are all the same rank (suit and color are irrelevant in
this game).

*Note: when playing a face-down card, you can only play that **one** card. Even if it's
revealed that you have another card of the same rank, you can't then play those as well.*

### Trump cards

Certain cards and plays act as "trump cards," which clear the pile of played cards from the table. Playing a trump card also grants the player an extra turn, where they can start a new pile with any card they choose.

The following are considered trump cards/plays:
- Any **ten**
- Any **jack**
- Completing a set of **four cards of the same rank**. This is cumulative across turns. For example, if one player plays two kings and the next player plays another king, the following player can play the fourth king to clear the pile. This is called a "swoop."

If a player cannot play a valid card (lower than or equal to the previous card), they must pick up the entire pile of played cards.

Once the pile is played down to an ace, subsequent players must either play an ace, a trump card, or pick up the pile.

### Scoring

As mentioned, like golf you want fewer points. Once one player has cleared all cards 
from their hand, the others are scored like so:

- **Five points** for number cards (ace through nine)
- **Ten points** for face cards (queens and kings)
- **Twenty-five points** for trump cards (tens and jacks)

You really want to get rid of all your trump cards before the round ends!

The game continues until one player reaches the threshold, which is typically set at
100-200 points. The player with the lowest score at that time wins the game.

