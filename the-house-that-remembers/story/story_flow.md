## Story flow
### Arrival and ordinary conversation

After receiving your friend's letter, you arrive at his house. Your friend is your childhood friend, and you used to spend time here in their house. It's been a long time since you saw each other. 

The friend is exhausted, glad you came, and tries to behave normally. He can make small talk, but doesn't explain the house’s history yet. He is clearly unwell and a lot of things he says don't add up. 

### Contradictions emerge
He talks as though his family is around: his mother is resting, his father is busy, his sister is nearby. Details in the house begin to make that seem unlikely, there is nobody else around and the house is dusty.

### The house’s frozen routines
Clues such as the stopped clock, old calendar, untouched food, and extra place setting suggest that time and daily life in the house have stopped or become distorted.

### The sister’s warnings
The engine triggers her first appearance after a few turns; later appearances can recur after a cooldown. She warns the player to leave. Her motive is protective, she clings to the belief that preserving the family keeps them together.

### The parents’ fragments and locked door
Knocking, footsteps, humming, and the note point toward the bedroom. The note reads “Do not open / Do not change / I have to keep things as they are.” These clues are meant to build dread without explaining the family’s fate.

### Opening the bedroom
The door opens only if all three fragments are complete and denial is 3 or lower. The player still has to enter the room; entering sets truth_known.

### The friend gradually faces the family story
If denial is below 3 and he is in the same room, each conversation can authorize one of four memories: the mother’s decline and the family’s deaths; the father’s attempt to preserve them; the sister’s hope; and the friend’s conflict, fear, and silence.

## Endings

- Escape Together: requires the truth to be faced, denial below 3, all four memories shared, and the player to choose to leave together.
- Escape Alone: the player leaves the house. This remains possible before or after learning the truth.
- Denial: can occur after three premature blunt confrontations, or at the 90-turn limit if the truth is still unknown.
- Sister's bargain: after her two warnings and a cooldown, the sister can have a private conversation with the player when their friend is elsewhere. On the player's fifth conversation turn, she asks them to leave the house and everything behind to preserve the family; choosing to leave triggers this ending, while choosing to stay lets the story continue.

## Main engine rules
The sidebar tracks 3 Memory Fragments: Past, Present, and Echoes, each completed by finding at least 2 clues in that category. All three fragments are needed for the door. The fragment categories—not just the overall clue count—are what matter for the door.
Denial starts at 8. Each new clue lowers it by 1. Up to three supportive actions can lower it by 1 each.
Before all fragments are complete, a blunt statement that the family is dead raises denial and increments the confrontation counter. The third such confrontation ends the game. Once all fragments are complete, confrontation lowers denial instead.
Movement and puzzle state are engine-owned. The model narrates what the engine confirms; it shouldn’t silently open doors, move characters, or add clues.

## Progression
The broad structure is: notice the family-shaped absences → investigate the house’s rules → hear the sister’s warning → confront the bedroom → let the friend work through what happened. 

A few details:

- The three fragments unlock the door, but don’t specifically unlock each family memory. After denial is low, any face-to-face conversation can advance one memory. That keeps the story flexible, but the four revelations could come quickly if the player asks several questions in a row.
- The together ending is a conversational trigger. The player doesn’t have to be in the Entrance Hall or actually walk out; saying a recognized “leave together” phrase can end the game from the bedroom. That may be fine as a narrated ending, but it’s less literal than the alone ending.
- The friend can only reach denial 3 or lower when the door opens. So after entering, “still resisting” is a narrow state, not prolonged high denial. That matches a story where opening the door already represents meaningful progress, but it means the bad ending after seeing the truth mainly depends on not lowering denial further before turn 90.