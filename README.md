# Hacktoberfest Open-Source AI - Week 4

## The House That Remembers

This is my submission for Hacktoberfest Open-Source AI Challenge: Week 4. This Week's Theme: Ghost in the Machine - 
Build something spooky, or something that honors the past in the spirit of Día de los Muertos, with open-weight models or open-source AI.

Because I love the spooky season, DnD (and reading crazy thrillers 😅), I decided to built a short DnD-style game. I call it _The House That Remembers_, inspired by The Fall of the House of Usher written by Edgar Allan Poe in 1839. There are very big spoilers in the /story folder. If you want to enjoy the game, I recommend not checking the story files. 

Tech stack:
- Streamplit - app.py: UI, chat interface
- Python - for logic, validates actions, updated history, clues, inventory
- Ollama + Gemma - narrates the permitted outcome

### Premise
_The letter arrived three nights ago, its paper creased and stained, the handwriting unmistakably your friend's — though the words were unlike anything you had ever known him to write._

_"Please, you must come. There are things in this house I can no longer explain. I fear it is too late for me. You are the only one I can trust."_

_Now, you stand before his ancestral home. Rain lashes against your face, and thunder rolls across the darkened sky. The house looms above you, its crooked silhouette barely visible through the mist. Tall, narrow windows stare down like hollow eyes. Ivy claws at the weathered stone walls, and the iron gates behind you groan in the wind, slowly swinging shut. Something about the place feels wrong. The air is unnaturally cold, carrying the scent of wet earth and rotting leaves. Though no lights burn inside, you cannot shake the feeling that someone is watching you from the upper windows._

_For a moment, lightning illuminates the facade — and you could swear a shadow has just moved behind the glass._

_Then the thunder cracks._

_The front door stands slightly ajar._

_Your friend invited you here for help. But as you stare into the darkness beyond the threshold, a troubling thought creeps into your mind:_

_Did he invite you into the house… or did the house invite you in?_

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
