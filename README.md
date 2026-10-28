# Hacktoberfest Open-Source AI - Week 4

## The House That Remembers

This is my submission for Hacktoberfest Open-Source AI Challenge: Week 4. This Week's Theme: Ghost in the Machine - 
Build something spooky, or something that honors the past in the spirit of Día de los Muertos, with open-weight models or open-source AI.

Because I love the spooky season, DnD (and reading crazy thrillers 😅), I decided to built a short DnD-style game. I call it _The House That Remembers_, inspired by The Fall of the House of Usher written by Edgar Allan Poe in 1839. There are very big spoilers in the /story folder. If you want to enjoy the game, I recommend not checking the story files. 

Tech stack:
- Streamlit - app.py: UI, chat interface
- Python - for logic, validates actions, updated history, clues, inventory
- Ollama + Gemma - narrates the permitted outcome

Trigger warnings: it is a horror story! There is no gore, but there are mentions of death and similar themes. 

### Premise
_The letter arrived three nights ago, its paper creased and stained, the handwriting unmistakably your friend's — though the words were unlike anything you had ever known him to write._

_"Please, you must come. There are things in this house I can no longer explain. I fear it is too late for me. You are the only one I can trust."_

_Now, you stand before his ancestral home. Rain lashes against your face, and thunder rolls across the darkened sky. The house looms above you, its crooked silhouette barely visible through the mist. Tall, narrow windows stare down like hollow eyes. Ivy claws at the weathered stone walls, and the iron gates behind you groan in the wind, slowly swinging shut. Something about the place feels wrong. The air is unnaturally cold, carrying the scent of wet earth and rotting leaves. Though no lights burn inside, you cannot shake the feeling that someone is watching you from the upper windows._

_For a moment, lightning illuminates the facade — and you could swear a shadow has just moved behind the glass._

_Then the thunder cracks._

_The front door stands slightly ajar._

_Your friend invited you here for help. But as you stare into the darkness beyond the threshold, a troubling thought creeps into your mind:_

_Did he invite you into the house… or did the house invite you in?_

### Tips for interacting with the story

Describe your actions, you're not stuck, and a lot of things are allowed! Think about your goal and what you are hoping to achieve. There is no right or wrong way to play this game. This games is based on TTRPG-style of games, where you are role-playing a character. The model serves as "DM" (Dungeon Master) - the narrator. He is the storyteller, the referee, maintains the setting in which the game is happening, and plays roles of "NPCs" (non-player characters). 

The narrator distinguishes spoken dialogue, physical actions, exploration, and
questions about the player's memories. You can make the intent clear in natural
language:

- Speak to your friend: `What can I do for you?` or `I say, "Let's go."`
- Combine speech and an action: `I pat him on the back and say, "Let's go."`
- Explore or examine: `Look around` or `Examine the family photos.`
- Recall an established memory: `What do I remember about my friend?`
- Move: `I walk to the library.`

Memory answers are limited to details already established in the story; the
narrator should not invent shared history.

### Run the Streamlit app

Install Ollama and download the model before starting the app:

```powershell
ollama pull gemma4:e4b
```

Make sure the Ollama service is running. Then, from the repository root, install the project dependencies: (optional: create and activate a virtual environment)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start the app with:

```powershell
python -m streamlit run .\the-house-that-remembers\app.py
```

Streamlit prints a local URL in the terminal; open it in your browser to view the app.
