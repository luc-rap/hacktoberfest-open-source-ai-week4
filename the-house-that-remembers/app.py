import base64
import json
from pathlib import Path

import ollama
import streamlit as st


MODEL_NAME = "gemma4:e4b"
CANON_PATH = Path(__file__).resolve().parent / "story" / "canon.json"
CANON = json.loads(CANON_PATH.read_text(encoding="utf-8"))

INTRO = '''
The letter arrived three nights ago, its paper creased and stained, the handwriting unmistakably your friend's — though the words were unlike anything you had ever known him to write.

_"Please, you must come. There are things in this house I can no longer explain. 
I fear it is too late for me. You are the only one I can trust."_

Now, you stand before his ancestral home.
Rain lashes against your face, and thunder rolls across the darkened sky. The house looms above you, its crooked silhouette barely visible through the mist. Tall, narrow windows stare down like hollow eyes. Ivy claws at the weathered stone walls, and the iron gates behind you groan in the wind, slowly swinging shut.
Something about the place feels wrong. The air is unnaturally cold, carrying the scent of wet earth and rotting leaves. Though no lights burn inside, you cannot shake the feeling that someone is watching you from the upper windows.

For a moment, lightning illuminates the facade — and you could swear a shadow has just moved behind the glass.

Then the thunder cracks.

The front door stands slightly ajar.

Your friend invited you here for help. But as you stare into the darkness beyond the threshold, a troubling thought creeps into your mind:

_Did he invite you into the house… or did the house invite you in?_
'''


def generate_response():
    room = ROOMS[st.session_state.room]
    friend = CANON["character_dynamics"]["friend"]
    system_prompt = (
        "You are the narrator for a gothic-horror interactive story, called The House That Remembers. "
        "Write grounded, immersive scenes with restrained horror. Respond directly to the player's actions and preserve their freedom to choose what to do."
        "Keep the whole reply to 2–5 short sentences. "
        "Preserve player's agency, the story should move on after 3-4 interactions, guide the player towards next story point"
        "Keep dialogue natural and concise. Characters should behave according to their personalities and knowledge. Avoid melodrama, excessive metaphors, repetitive descriptions, and unnecessary exposition. Ordinary, quiet moments are part of the story; not every turn needs a clue or scare."
        "He may pause, answer briefly, trail off, or change "
        "the subject. He does not understand the supernatural situation "
        "clearly and cannot explain it neatly. Respond naturally to the "
        "player's suggestions and offers; do not assume any particular "
        "activity. When he accepts a reasonable suggestion, let him take "
        "initiative and follow through with the next small action."
        "Keep actions consistent with the player's choices and available "
        "exits. Only mention shared memories or family details already "
        "established in the conversation or canon; do not invent them. Do "
        "not introduce a warning, clue, supernatural event, invitation, or "
        "change of location without a reason."
        "Preserve game state: do not claim the player gained "
        "items, discovered clues, or changed rooms unless the state says so. "
        "A character may invite the player to move, but the move only happens "
        "after the player chooses it. Keep unrevealed canon secrets hidden.\n\n"
        "Story premise:\n"
        f"{CANON['premise']['summary']}\n\n"
        "Friend's established characterization:\n"
        f"Initial state: {friend['initial_state']}\n"
        f"Early behavior: {friend['early_behavior']}\n\n"
        f"Friend's voice: {friend['voice']}\n\n"
        "Urgent letter the friend sent:\n"
        f"{CANON['opening']['letter_text']}\n\n"
        "Narrator rules:\n"
        f"{json.dumps(CANON['narrator_contract'], ensure_ascii=False)}\n\n"
        f"Current room: {st.session_state.room}\n"
        f"Room description: {room['description']}\n"
        f"Available exits: {', '.join(room['exits'])}\n"
        f"Inventory: {', '.join(st.session_state.inventory) or 'empty'}\n"
        f"Clues: {', '.join(st.session_state.clues) or 'none'}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        *st.session_state.history,
    ]
    result = ollama.chat(
        model=MODEL_NAME,
        messages=messages,
        think=False,
        options={
            "temperature": 0.6,
            "num_predict": 128,
        },
    )
    return result.message.content.strip()


def play_background_music(file_path, loop=True):
    audio_path = Path(file_path)
    if not audio_path.is_absolute():
        audio_path = Path(__file__).resolve().parent / audio_path
    audio_base64 = base64.b64encode(audio_path.read_bytes()).decode("ascii")
    loop_attr = "loop" if loop else ""
    st.markdown(
        f"""
        <audio controls {loop_attr} style="width: 100%;">
            <source
                src="data:audio/mpeg;base64,{audio_base64}"
                type="audio/mpeg"
            >
        </audio>
        """,
        unsafe_allow_html=True,
    )

# ---------- Styling ----------
st.markdown("""
<style>
.stApp {
    background: #171719;
    color: #e8ddca;
}
[data-testid="stSidebar"] {
    background: #222124;
    border-right: 1px solid #45413d;
}
h1, h2, h3 {
    color: #e8ddca !important;
    font-family: Georgia, serif;
}
.story {
    font-family: Georgia, serif;
    font-size: 1.08rem;
    line-height: 1.9;
    color: #d8d1c7;
}
.muted {
    color: #a7a19a;
    font-size: 0.85rem;
    letter-spacing: 0.12em;
}
div[data-testid="stChatMessage"] {
    background: #222124;
    border: 1px solid #34312e;
    border-radius: 12px;
}
.stChatInput textarea {
    color: #e8ddca !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- Game data ----------
ROOMS = {
    "Entrance Hall": {
        "description": (
            "The moment you step inside, a gust of wind slips past you. The heavy front door slams shut behind you with a deafening BANG. The sound echoes through the vast entrance hall, bouncing off the high ceilings before dissolving into silence. \n\n"
            "A figure emerges from the shadows. Your friend.\n"
            "He looks nothing like the person you remember. His eyes are hollow, his skin pale, ghostly, and dark circles hollow his eyes.\n\n"
            "\"You came,\" he whispers, his voice trembling. \"I didn't think anyone would.\"\n\n"
            "He steps closer whispers in a voice that is barely audible\n\n"
            "\"I need your help...\""
        ),
        "exits": ["Library", "Kitchen", "Grand Staircase"],
        "img": "hallway.jpg"
    },
    "Library": {
        "description": (
            "Shelves of warped books climb toward a ceiling lost "
            "in shadow. One narrow gap interrupts the dust on a "
            "lower shelf, as though a book was recently removed."
        ),
        "exits": ["Entrance Hall"],
    },
    "Kitchen": {
        "description": (
            "The narrow kitchen is cluttered but familiar. Rain ticks "
            "against a dark window above the sink. A kettle, a chipped "
            "teapot, and two mismatched cups sit on the counter."
        ),
        "exits": ["Entrance Hall"],
    },
    "Grand Staircase": {
        "description": (
            "The staircase groans beneath your weight. At the "
            "landing, a portrait hangs crookedly. From above "
            "comes the faint sound of someone humming."
        ),
        "exits": ["Entrance Hall"],
    },
}

# ---------- Session state ----------
if "room" not in st.session_state:
    st.session_state.room = "Entrance Hall"

if "inventory" not in st.session_state:
    st.session_state.inventory = ["The Letter"]

if "clues" not in st.session_state:
    st.session_state.clues = []

if "history" not in st.session_state:
    st.session_state.history = [
        {
            "role": "assistant",
            "content": (
                "\"I need your help...\""
            ),
        }
    ]

if "visited" not in st.session_state:
    st.session_state.visited = ["Entrance Hall"]

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 🕯️ THE HOUSE")
    st.markdown('<p class="muted">YOUR PRIVATE RECORD</p>',
                unsafe_allow_html=True)

    st.divider()

    st.markdown("### 📍 Current location")
    st.write(st.session_state.room)

    st.markdown("### 🎒 Inventory")
    if st.session_state.inventory:
        for item in st.session_state.inventory:
            st.write(f"• {item}")
    else:
        st.caption("Your pockets are empty.")

    st.markdown("### 🔎 Clues")
    if st.session_state.clues:
        for clue in st.session_state.clues:
            st.write(f"• {clue}")
    else:
        st.caption("Nothing discovered yet.")

    st.markdown("### 🗺️ Explored")
    for room in st.session_state.visited:
        st.write(f"✓ {room}")

    st.divider()

    if st.button("Restart adventure", use_container_width=True):
        for key in ("room", "inventory", "clues", "history", "visited"):
            st.session_state.pop(key, None)
        st.rerun()

# ---------- Main screen ----------
st.markdown(
    '<p class="muted">A GOTHIC HORROR ADVENTURE</p>',
    unsafe_allow_html=True,
)
st.title("The House That Remembers")

st.caption("CHAPTER I  ·  THE ARRIVAL")


with st.sidebar:
    st.subheader("🔊 Atmosphere")

    sound_enabled = st.checkbox(
        "🌧️ Background rain",
        value=True,
    )

    if sound_enabled:
        play_background_music(Path("assets") / "rain-and-thunder.mp3")

st.image(
    Path(__file__).resolve().parent / "assets" / "haunted_house.jpg",
    width='stretch'
)

st.divider()

st.markdown(INTRO)

room = ROOMS[st.session_state.room]

st.markdown(f"### 📍 {st.session_state.room}")
if "img" in room:
    st.image(
        Path(__file__).resolve().parent / "assets" / room["img"],
        width='stretch'
    )

st.markdown(
    f'<div class="story">{room["description"]}</div>',
    unsafe_allow_html=True,
)

st.divider()

# ---------- Suggested actions ----------
# st.markdown("**What will you do?**")

# col1, col2, col3 = st.columns(3)

#with col1:
#    examine = st.button("🔍 Examine surroundings",
#                        use_container_width=True)

#with col2:
#    explore = st.button("🚪 Explore another room",
#                        use_container_width=True)

#with col3:
#    inspect = st.button("🗝️ Inspect the letter opener",
#                        use_container_width=True)

# Convert buttons into ordinary game actions.
action = None

#if examine:
#    action = "examine surroundings"
#elif explore:
#    action = "explore another room"
#elif inspect:
#    action = "inspect the letter opener"

# ---------- Free-text action input ----------
typed_action = st.chat_input("Describe what you do...")
if typed_action:
    action = typed_action

# ---------- Action handling ----------
if action:
    st.session_state.history.append({
        "role": "user",
        "content": action,
    })

    text = action.lower()

    if "letter opener" in text or "opener" in text:
        if "Silver letter opener" not in st.session_state.inventory:
            st.session_state.inventory.append("Silver letter opener")

    elif destination := next(
        (
            exit_name
            for exit_name in ROOMS[st.session_state.room]["exits"]
            if exit_name.lower() in text
        ),
        None,
    ):
        st.session_state.room = destination
        if destination not in st.session_state.visited:
            st.session_state.visited.append(destination)

    elif "library" in text:
        if st.session_state.room != "Library":
            st.session_state.room = "Library"
            if "Library" not in st.session_state.visited:
                st.session_state.visited.append("Library")

    elif "upstairs" in text or "staircase" in text:
        if st.session_state.room != "Grand Staircase":
            st.session_state.room = "Grand Staircase"
            if "Grand Staircase" not in st.session_state.visited:
                st.session_state.visited.append("Grand Staircase")

    elif "book" in text or "shelf" in text:
        if st.session_state.room == "Library":
            clue = "A book was recently removed from the shelf"
            if clue not in st.session_state.clues:
                st.session_state.clues.append(clue)

    try:
        with st.spinner("Thinking..."):
            response = generate_response()
    except ollama.ResponseError as error:
        if error.status_code == 404:
            st.session_state.ollama_error = (
                f"Ollama could not find {MODEL_NAME}. "
                f"Run `ollama pull {MODEL_NAME}` and try again."
            )
        else:
            st.session_state.ollama_error = (
                f"Ollama returned an error: {error.error}"
            )
    except ollama.RequestError as error:
        st.session_state.ollama_error = (
            "Could not connect to Ollama. Make sure Ollama is running, "
            f"then try again. Details: {error}"
        )
    else:
        if response:
            st.session_state.pop("ollama_error", None)
            st.session_state.history.append({
                "role": "assistant",
                "content": response,
            })
        else:
            st.session_state.ollama_error = (
                "Ollama returned an empty response. Please try again."
            )

    st.rerun()

# ---------- Conversation ----------
st.markdown("### What will you do?")

for message in st.session_state.history:
    with st.chat_message(message["role"], avatar="🕯️" if message["role"] == "assistant" else "🧑"):
        st.markdown(message["content"])

if "ollama_error" in st.session_state:
    st.error(st.session_state.ollama_error)

st.caption(f"Powered by Ollama · {MODEL_NAME}")
