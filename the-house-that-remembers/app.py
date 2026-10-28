import base64
import copy
import json
from pathlib import Path

import ollama
import streamlit as st

from engine import ROOMS, apply_action, new_game
from prompt import build_messages, generation_options, maybe_summarize, tidy

st.set_page_config(page_title="The House That Remembers", layout="wide")

MODEL_NAME = "gemma4:e4b"
CANON_PATH = Path(__file__).resolve().parent / "story" / "canon.json"
CANON = json.loads(CANON_PATH.read_text(encoding="utf-8"))

INTRO = '''
The letter arrived three nights ago, its paper creased and stained, the handwriting unmistakably your friend's — though the words were unlike anything you had ever known him to write.

_"Please, you must come. There are things in this house I can no longer explain. 
I fear it is too late for me. You are the only one I can trust."_

Now, you stand before his home.
Rain lashes against your face, and thunder rolls across the darkened sky. The house looms above you, its crooked silhouette barely visible through the mist. Tall, narrow windows stare down like hollow eyes. Ivy claws at the weathered stone walls, and the iron gates behind you groan in the wind, slowly swinging shut.

You remember this house from your childhood, but something about it feels wrong. 
You used to play outside, spend time helping your friend with chores in the kitchen, explore the family library, and even sleep over in the guest room.

The air is unnaturally cold, carrying the scent of wet earth and rotting leaves. Though no lights burn inside, you cannot shake the feeling that someone is watching you from the upper windows.

For a moment, lightning illuminates the facade — and you could swear a shadow has just moved behind the glass.

Then the thunder cracks.

The front door stands slightly ajar.

Your friend invited you here for help. But as you stare into the darkness beyond the threshold, a troubling thought creeps into your mind:

_Did he invite you into the house… or did the house invite you in?_
'''


def generate_response(game):
    result = ollama.chat(
        model=MODEL_NAME,
        messages=build_messages(game, CANON),
        think=False,
        options=generation_options(game),
    )
    return tidy(result.message.content)


def show_image(path, **kwargs):
    """Show an image, or a quiet caption if the file is missing (instead of crashing the app)."""
    if Path(path).exists():
        st.image(path, **kwargs)
    else:
        st.caption(f"(image not found: {Path(path).name})")


def play_background_music(file_path, loop=True):
    audio_path = Path(file_path)
    if not audio_path.is_absolute():
        audio_path = Path(__file__).resolve().parent / audio_path
    if not audio_path.exists():
        st.caption(f"(audio not found: {audio_path.name})")
        return
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

# ---------- Session state ----------
if "game" not in st.session_state:
    st.session_state.game = new_game()
game = st.session_state.game

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 🕯️ THE HOUSE")
    st.markdown('<p class="muted">YOUR PRIVATE RECORD</p>',
                unsafe_allow_html=True)

    st.divider()

    st.markdown("### 📍 Current location")
    st.write(game["room"])

    st.markdown("### 🎒 Inventory")
    if game["inventory"]:
        for item in game["inventory"]:
            st.write(f"• {item}")
    else:
        st.caption("Your pockets are empty.")

    st.markdown("### 🔎 Clues")
    if game["clues"]:
        for clue in game["clues"]:
            st.write(f"• {clue}")
    else:
        st.caption("Nothing discovered yet.")

    st.markdown("### 🗺️ Explored")
    for visited_room in game["visited"]:
        st.write(f"✓ {visited_room}")

    st.divider()

    if st.button("Restart adventure", use_container_width=True):
        st.session_state.pop("game", None)
        st.session_state.pop("ollama_error", None)
        st.rerun()

    st.subheader("🔊 Atmosphere")
    sound_enabled = st.checkbox("🌧️ Background rain", value=True)
    if sound_enabled:
        play_background_music(Path("assets") / "rain-and-thunder.mp3")
    house_ambience_enabled = st.checkbox("🏚️ House ambience", value=True)
    if house_ambience_enabled:
        play_background_music(Path("assets") / "ambience.mp3")

# ---------- Main screen ----------
st.markdown('<p class="muted">A GOTHIC HORROR ADVENTURE</p>',
            unsafe_allow_html=True)
st.title("The House That Remembers")

with st.expander("The letter and arrival", expanded=True):
    _, image_column, _ = st.columns([1, 2, 1])
    with image_column:
        show_image(
            Path(__file__).resolve().parent / "assets" / "haunted_house.jpg",
            width=480,
        )
    st.markdown(INTRO)

scene_column, conversation_column = st.columns([1, 1.25], gap="large")
room = ROOMS[game["room"]]

with scene_column:
    with st.container(height="content", border=True):
        st.markdown(f"### 📍 {game['room']}")
        if "img" in room:
            show_image(
                Path(__file__).resolve().parent / "assets" / room["img"],
                width='stretch',
            )
        else:
            st.caption("No image is available for this room yet.")
        st.markdown(
            f'<div class="story">{room["description"]}</div>',
            unsafe_allow_html=True,
        )

with conversation_column:
    thinking_placeholder = st.empty()
    st.markdown("### What will you do?")
    with st.container(height=480, border=True, autoscroll=True):
        for message in game["history"]:
            with st.chat_message(
                message["role"],
                avatar="🕯️" if message["role"] == "assistant" else "🧑",
            ):
                st.markdown(message["content"])

        if game["ending"]:
            st.markdown("---")
            st.markdown("**THE END**")

        if "ollama_error" in st.session_state:
            st.error(st.session_state.ollama_error)

    action = st.chat_input(
        "Describe what you do...",
        disabled=bool(game["ending"]),
    )

if action:
    snapshot = copy.deepcopy(game)          # restore this if the model call fails
    game["history"].append({"role": "user", "content": action})
    apply_action(game, action)              # Python decides what actually happened

    error_message = None
    response = ""
    try:
        with thinking_placeholder.container():
            with st.spinner("Thinking..."):
                maybe_summarize(game, MODEL_NAME)
                response = generate_response(game)
    except ollama.ResponseError as error:
        if error.status_code == 404:
            error_message = (
                f"Ollama could not find {MODEL_NAME}. "
                f"Run `ollama pull {MODEL_NAME}` and try again."
            )
        else:
            error_message = f"Ollama returned an error: {error.error}"
    except ollama.RequestError as error:
        error_message = (
            "Could not connect to Ollama. Make sure Ollama is running, "
            f"then try again. Details: {error}"
        )
    else:
        if not response:
            error_message = "Ollama returned an empty response. Please try again."

    if error_message:
        st.session_state.game = snapshot    # undo the failed turn completely
        st.session_state.ollama_error = error_message
    else:
        st.session_state.pop("ollama_error", None)
        game["history"].append({"role": "assistant", "content": response})

    st.rerun()

st.caption(f"Powered by Ollama · {MODEL_NAME}")