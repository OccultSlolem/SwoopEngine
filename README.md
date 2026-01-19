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

**Swoop** is a card game where players compete to collect the most points by playing
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

You can clear all the cards on the table by playing a *trump card*, accomplished by
playing a ten, jack, or four cards of the same rank. That last one can include cards from
previous players - for instance, if the one player put down two kings, the next one put
down another king, the one following could swoop by placing a fourth king. Doing this
grants the player an extra turn where they can play whatever they want.

If a player does not have any cards available to play, they must pick up all cards on
the table that have been played since the previous trump card. Once the table is played
down to an ace, the following players must either continue to play aces, play a trump
card, or pick up the deck if they don't have anything to play. The round ends when
**one** player has gotten all the cards out their deck.

### Scoring

As mentioned, like golf you want fewer points. Once one player has cleared all cards 
from their hand, the others are scored like so:

- **Five points** for number cards (ace through nine)
- **Ten points** for face cards (queens and kings)
- **Twenty-five points** for trump cards (tens and jacks)

You really want to get rid of all your trump cards before the round ends!

