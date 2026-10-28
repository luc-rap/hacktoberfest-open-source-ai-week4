import base64
import copy
import json
from io import BytesIO
from pathlib import Path

import ollama
import streamlit as st
from PIL import Image

from engine import (
    FINAL_REVELATIONS,
    FRAGMENT_LABELS,
    FRAGMENT_KINDS,
    FRAGMENT_CLUES_NEEDED,
    ROOMS,
    apply_action,
    fragment_progress,
    fragments_complete,
    new_game,
)
from prompt import build_messages, generation_options, maybe_summarize, tidy

st.set_page_config(page_title="The House That Remembers", layout="wide")
st.markdown(
    "<link rel='stylesheet' "
    "href='https://cdn-uicons.flaticon.com/uicons-solid-straight/css/"
    "uicons-solid-straight.css'>",
    unsafe_allow_html=True,
)
st.markdown(
    "<link rel='stylesheet' "
    "href='https://cdn-uicons.flaticon.com/uicons-bold-straight/css/"
    "uicons-bold-straight.css'>",
    unsafe_allow_html=True,
)

MODEL_NAME = "gemma4:e4b"
CANON_PATH = Path(__file__).resolve().parent / "story" / "canon.json"
CANON = json.loads(CANON_PATH.read_text(encoding="utf-8"))

INTRO = '''
The letter arrived three nights ago, its paper creased and stained, the handwriting unmistakably your friend's — though the words were unlike anything you had ever known him to write.

_"Please, you must come. There are things in this house I can no longer explain. 
I'm afraid it may be too late for me. You're the only person I can trust."_

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


@st.cache_data(show_spinner=False)
def haunted_house_banner():
    image_path = Path(__file__).resolve().parent / "assets" / "haunted_house.jpg"
    if not image_path.exists():
        return ""
    with Image.open(image_path) as image:
        image.thumbnail((1800, 900))
        optimized = BytesIO()
        image.convert("RGB").save(optimized, format="JPEG", quality=82, optimize=True)
    return base64.b64encode(optimized.getvalue()).decode("ascii")


@st.dialog("The Letter", width="small")
def show_letter_dialog():
    letter_path = Path(__file__).resolve().parent / "assets" / "letter.png"
    show_image(letter_path, width="stretch")


@st.dialog("The Book", width="small")
def show_book_dialog():
    book_path = Path(__file__).resolve().parent / "assets" / "book.png"
    show_image(book_path, width="stretch")
    st.markdown(
        '**"The Fall of the House of Usher" by Edgar Allan Poe is a short story '
        "first published in 1839. A narrator visits his ailing childhood friend "
        "Roderick Usher at his decaying family mansion. There he encounters "
        "Roderick's mysterious twin sister Madeline, who suffers from a strange "
        "illness. As the atmosphere grows increasingly oppressive, the house "
        "itself seems alive with malevolent energy. When Madeline is entombed "
        "within the estate, terrifying sounds begin echoing through the halls, "
        "building toward a shocking climax that binds the fate of the twins to "
        'their ancestral home."**'
    )


@st.dialog("The Note", width="small")
def show_note_dialog():
    note_path = Path(__file__).resolve().parent / "assets" / "note.png"
    show_image(note_path, width="stretch")


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
body, .stApp, .stApp input, .stApp textarea, .stApp button {
    font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif !important;
}
.stApp {
    background: var(--house-background, #171719);
    color: #e8ddca;
    transition: background 1.2s ease;
}
[data-testid="stMainBlockContainer"] {
    padding-top: 0;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #17191a 0%, #1c1d1d 55%, #171819 100%);
    border-right: 1px solid #39332d;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {
    margin: 0 0 0.15rem;
    color: #e7d4b8 !important;
    font-size: 1.18rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
    margin: 1.15rem 0 0.35rem;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid rgba(176, 132, 82, 0.22);
    color: #bda17e !important;
    font-size: 0.76rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}
.sidebar-icon-heading .fi {
    margin-right: 0.45rem;
    color: #b98b5e;
    font-size: 0.9em;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #c9c0b3;
    line-height: 1.55;
}
.sidebar-brand {
    padding: 0.35rem 0 0.85rem;
    border-bottom: 1px solid rgba(176, 132, 82, 0.32);
}
.sidebar-brand .brand-name {
    margin-bottom: 0.25rem;
    color: #e7d4b8;
    font-size: 1.05rem;
    letter-spacing: 0.14em;
}
.sidebar-brand .muted {
    color: #9d9386;
    font-size: 0.64rem;
    letter-spacing: 0.16em;
}
.sidebar-about {
    margin-top: 1.4rem;
    padding-top: 0.65rem;
    border-top: 1px solid rgba(176, 132, 82, 0.22);
    font-size: 0.78rem;
}
.sidebar-about a {
    color: #bda17e;
    text-decoration: none;
}
.sidebar-about a:hover {
    color: #eee1cd;
    text-decoration: underline;
}
h1, h2, h3 {
    color: #e8ddca !important;
    font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif !important;
}
.page-header {
    width: calc(100% + 10rem);
    min-height: 230px;
    margin: 0 -5rem 1.2rem;
    padding: 1.5rem calc(5rem + 1.75rem);
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    border-bottom: 1px solid rgba(176, 132, 82, 0.32);
    background-color: #17191a;
    background-position: center 43%;
    background-size: cover;
}
@media (max-width: 768px) {
    .page-header {
        width: 100%;
        margin-left: 0;
        padding: 1.25rem;
    }
}
.page-header .eyebrow {
    margin: 0 0 0.45rem;
    color: #bb8b58;
    font-size: 0.72rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
}
.page-header .title {
    margin: 0;
    color: #eee1cd;
    font-size: clamp(1.8rem, 3vw, 2.45rem);
    line-height: 1.1;
}
.page-header .subtitle {
    max-width: 42rem;
    margin: 0.55rem 0 0;
    color: #b9afa1;
    font-size: 1rem;
    font-style: italic;
    line-height: 1.55;
}
.st-key-scene_panel,
.st-key-conversation_frame {
    position: relative;
    outline: 1px solid rgba(176, 132, 82, 0.28);
    outline-offset: -1px;
    border-radius: 4px;
}
.st-key-scene_panel::before,
.st-key-conversation_frame::before {
    content: "";
    position: absolute;
    inset: 5px;
    z-index: 2;
    pointer-events: none;
    opacity: 0.72;
    background:
        linear-gradient(#bd9567, #bd9567) left top / 18px 1px no-repeat,
        linear-gradient(#bd9567, #bd9567) left top / 1px 18px no-repeat,
        linear-gradient(#bd9567, #bd9567) right top / 18px 1px no-repeat,
        linear-gradient(#bd9567, #bd9567) right top / 1px 18px no-repeat,
        linear-gradient(#bd9567, #bd9567) left bottom / 18px 1px no-repeat,
        linear-gradient(#bd9567, #bd9567) left bottom / 1px 18px no-repeat,
        linear-gradient(#bd9567, #bd9567) right bottom / 18px 1px no-repeat,
        linear-gradient(#bd9567, #bd9567) right bottom / 1px 18px no-repeat;
}
.story {
    font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif;
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
.stApp [data-testid="stMarkdownContainer"] {
    font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif;
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

if game.get("truth_known"):
    house_lighting = {
        "light": "rgba(119, 137, 143, 0.05)",
        "base": "#0d1112",
        "vignette": "rgba(0, 0, 0, 0.62)",
    }
elif game["stage"] >= 5:
    house_lighting = {
        "light": "rgba(92, 113, 127, 0.04)",
        "base": "#090d11",
        "vignette": "rgba(0, 0, 0, 0.84)",
    }
elif game["stage"] >= 4:
    house_lighting = {
        "light": "rgba(85, 109, 126, 0.045)",
        "base": "#0a0f13",
        "vignette": "rgba(0, 0, 0, 0.80)",
    }
elif game["stage"] >= 3:
    house_lighting = {
        "light": "rgba(93, 92, 119, 0.045)",
        "base": "#0d0e13",
        "vignette": "rgba(0, 0, 0, 0.76)",
    }
elif game["stage"] >= 2:
    house_lighting = {
        "light": "rgba(92, 119, 137, 0.05)",
        "base": "#0b1014",
        "vignette": "rgba(0, 0, 0, 0.72)",
    }
else:
    house_lighting = {
        "light": "rgba(107, 126, 137, 0.055)",
        "base": "#0c1114",
        "vignette": "rgba(0, 0, 0, 0.68)",
    }

st.markdown(
    f"""
    <style>
    .stApp {{
        --house-background:
            radial-gradient(ellipse at 50% 12%, {house_lighting["light"]}, transparent 58%),
            radial-gradient(ellipse at center, transparent 38%, {house_lighting["vignette"]} 100%),
            {house_lighting["base"]};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand"><div class="brand-name">'
        '<i class="fi fi-ss-house-chimney" aria-hidden="true"></i> THE HOUSE</div>'
        '<div class="muted">YOUR PRIVATE RECORD</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<h3 class="sidebar-icon-heading"><i class="fi fi-ss-marker" '
        'aria-hidden="true"></i>Current location</h3>',
        unsafe_allow_html=True,
    )
    st.write(game["room"])

    st.markdown(
        '<h3 class="sidebar-icon-heading"><i class="fi fi-ss-user" '
        'aria-hidden="true"></i>Friend</h3>',
        unsafe_allow_html=True,
    )
    friend_room = game.get("friend_room", "Entrance Hall")
    st.write("Here with you" if friend_room == game["room"] else f"In the {friend_room}")

    st.markdown(
        '<h3 class="sidebar-icon-heading"><i class="fi fi-ss-puzzle-piece" '
        'aria-hidden="true"></i>Memory fragments</h3>',
        unsafe_allow_html=True,
    )
    completed_fragments = len(fragments_complete(game))
    st.write(f"**{completed_fragments}/3 complete**")
    fragment_status = fragment_progress(game)
    for kind in FRAGMENT_KINDS:
        progress = fragment_status[kind]
        marker = "✓" if progress["complete"] else "○"
        st.caption(
            f"{marker} {FRAGMENT_LABELS[kind]}: "
            f"{progress['found']}/{FRAGMENT_CLUES_NEEDED} clues"
        )

    if game.get("truth_known"):
        st.markdown("### Family memories")
        shared_memories = game.get("final_revelations", [])
        st.write(f"**{len(shared_memories)}/{len(FINAL_REVELATIONS)} remembered**")
        for memory in FINAL_REVELATIONS:
            if memory["id"] in shared_memories:
                st.caption(f"✓ {memory['title']}")

    st.markdown(
        '<h3 class="sidebar-icon-heading"><i class="fi fi-ss-box-open" '
        'aria-hidden="true"></i>Inventory</h3>',
        unsafe_allow_html=True,
    )
    if game["inventory"]:
        for item in game["inventory"]:
            if item == "The Letter":
                if st.button("The Letter · Inspect", key="open_letter"):
                    show_letter_dialog()
            elif item == "Library Book":
                if st.button("Library Book · Inspect", key="open_book"):
                    show_book_dialog()
            elif item == "Upper Landing Note":
                if st.button("Upper Landing Note · Inspect", key="open_note"):
                    show_note_dialog()
            else:
                st.write(f"• {item}")
    else:
        st.caption("Your pockets are empty.")

    st.markdown(
        '<h3 class="sidebar-icon-heading"><i class="fi fi-bs-search" '
        'aria-hidden="true"></i>Clues</h3>',
        unsafe_allow_html=True,
    )
    if game["clues"]:
        for clue in game["clues"]:
            st.write(f"• {clue}")
    else:
        st.caption("Nothing discovered yet.")

    st.markdown(
        '<h3 class="sidebar-icon-heading"><i class="fi fi-ss-door-open" '
        'aria-hidden="true"></i>Explored</h3>',
        unsafe_allow_html=True,
    )
    for visited_room in game["visited"]:
        st.write(f"✓ {visited_room}")

    st.divider()

    if st.button("Restart adventure", use_container_width=True):
        st.session_state.pop("game", None)
        st.session_state.pop("ollama_error", None)
        st.rerun()

    st.subheader("Atmosphere")
    sound_enabled = st.checkbox("Background rain", value=True)
    if sound_enabled:
        play_background_music(Path("assets") / "rain-and-thunder.mp3")
    house_ambience_enabled = st.checkbox("House ambience", value=True)
    if house_ambience_enabled:
        play_background_music(Path("assets") / "ambience.mp3")

    st.markdown(
        '<div class="sidebar-about"><a '
        'href="https://github.com/luc-rap/hacktoberfest-open-source-ai-week4" '
        'target="_blank" rel="noopener noreferrer">About · GitHub</a></div>',
        unsafe_allow_html=True,
    )

# ---------- Main screen ----------
banner_image = haunted_house_banner()
banner_style = ""
if banner_image:
    banner_style = (
        ' style="background-image: '
        'linear-gradient(90deg, rgba(10, 12, 14, 0.94) 0%, '
        'rgba(10, 12, 14, 0.72) 48%, rgba(10, 12, 14, 0.20) 100%), '
        'linear-gradient(0deg, rgba(15, 16, 17, 0.78), transparent 68%), '
        f'url(data:image/jpeg;base64,{banner_image});"'
    )
st.markdown(
    f'<header class="page-header"{banner_style}>'
    '<p class="eyebrow">A gothic horror adventure · Private journal</p>'
    '<h1 class="title">The House That Remembers</h1>'
    '<p class="subtitle">Some doors should stay closed.</p>'
    '</header>',
    unsafe_allow_html=True,
)

with st.expander("The letter and arrival", expanded=True):
    st.markdown(INTRO)

scene_column, conversation_column = st.columns([1, 1.25], gap="large")
room = ROOMS[game["room"]]

with scene_column:
    with st.container(height="content", border=True, key="scene_panel"):
        st.markdown(f"### {game['room']}")
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
    with st.container(key="conversation_frame"):
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