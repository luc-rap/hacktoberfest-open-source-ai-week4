"""engine.py - authoritative game state and rules.

Nothing in here calls the model. The model only ever sees the *result* of
what this module decides (see prompt.py).
"""
import re
from pprint import pprint


# Slow clue drip: during quiet turns the engine surfaces one small detail.
AMBIENT_AFTER_TURNS = 3   # turns spent in a room before a detail may surface
AMBIENT_COOLDOWN = 3      # minimum turns between any two noticed details
FRAGMENT_CLUES_NEEDED = 2  # clues of one kind needed to complete a memory fragment
FRAGMENT_KINDS = ("past", "present", "echoes")
FRAGMENT_LABELS = {
    "past": "Past",
    "present": "Present",
    "echoes": "Echoes",
}
DOOR_DENIAL_MAX = 3        # friend's denial must be at or below this to open the door
PUSH_LIMIT = 3             # blunt confrontations before the evidence -> he shuts down
SUPPORT_LIMIT = 3          # times kindness can lower his denial
MAX_TURNS = 90             # unresolved truth or denial by then -> "denial" ending
NUDGE_AFTER_TURNS = 4
NUDGE_COOLDOWN = 3
SISTER_COOLDOWN = 12
SISTER_CONVERSATION_LIMIT = 5

FINAL_REVELATIONS = (
    {
        "id": "mother",
        "title": "His mother's decline",
        "detail": (
            "They are dead. The house drained them, beginning with his mother, who "
            "grew exhausted and unable to sleep and sensed something was wrong. The "
            "room was preserved, so they look as if they are sleeping."
        ),
    },
    {
        "id": "father",
        "title": "His father's attempt to preserve them",
        "detail": (
            "After help failed, his father became frightened and tried to preserve "
            "the family unchanged. He locked himself, his wife, and his daughter in "
            "the bedroom and told his son never to open the door. He thought he was "
            "protecting them, but shut them away from help; they died there, drained "
            "by the house."
        ),
    },
    {
        "id": "sister",
        "title": "His sister's hope",
        "detail": (
            "His sister kept trying to hold the family together and urged her brother "
            "not to give up on them. Now she clings to the house's preserved illusion, "
            "believing it keeps her family together; her warnings to leave are real, "
            "but she mistakes letting go for losing them."
        ),
    },
    {
        "id": "friend",
        "title": "Why he stayed silent",
        "detail": (
            "He had argued with his father and believed the others were overreacting. "
            "He knocked once, heard no answer, and obeyed the last order out of anger "
            "and fear. Since then he has pretended they were still alive and resting, "
            "unable to face that he never opened the door."
        ),
    },
)

SISTER_PRESERVATION_MEMORY = (
    "She believes the family is still together as long as the house preserves them "
    "exactly as they were. To her, keeping things unchanged is a way of keeping them "
    "alive; she warns the player away because she fears that facing the truth will "
    "make her lose them."
)

# ---------------------------------------------------------------------------
# World data
# ---------------------------------------------------------------------------
# "features" are things the player can examine/take. "looks" is what each
# successive examination reveals (the last entry repeats). Each "clue" is
# (clue text, examination number, fragment kind); None marks a discovery that
# does not count toward fragment progress.
ROOMS = {
    "Entrance Hall": {
        "description": (
            "The moment you step inside, a gust of wind slips past you. The heavy front door slams shut behind you with a deafening BANG. The sound echoes through the vast entrance hall, bouncing off the high ceilings before dissolving into silence. \n\n"
            "A figure emerges from the shadows. Your friend.\n"
            "He looks nothing like the person you remember. His eyes are hollow, his skin pale, ghostly, and dark circles hollow his eyes.\n\n"
            "\"You came,\" he whispers, his voice trembling. \"I didn't think you would... Thank you.\"\n\n"
        ),
        "exits": ["Library", "Kitchen", "Grand Staircase"],
        "img": "hallway.jpg",
        "aliases": ["entrance hall", "entrance", "hallway", "hall", "foyer"],
        "features": {
            "smell": {
                "ambient": True,
                "keywords": ["smell", "scent", "odor", "musty"],
                "looks": ["A musty smell lingers in the air, a mixture of old wood and dust."],
                "clues": [("A musty smell lingers in the air", 1, None)],
            },
            "clock": {
                "ambient": True,
                "keywords": ["clock", "clocks", "pendulum", "ticking"],
                "looks": [
                    "A tall clock stands against the wall, its hands stopped at a quarter past three. The pendulum hangs perfectly still. The clock hasn't moved. Nothing in this hall ticks.",
                ],
                "clues": [("The clock on the wall is frozen at 3:15", 1, 'past')],
                "friend": "He says it only needs winding, then changes the subject.",
            },
        },
    },
    "Library": {
        "description": (
            "Shelves of warped books climb toward a ceiling lost "
            "in shadow. One narrow gap interrupts the dust on a "
            "lower shelf, as though a book was recently removed. Family photos are hanging on the walls, but the faces are blurred and unrecognizable. "
        ),
        "exits": ["Entrance Hall"],
        "img": "library.jpg",
        "aliases": ["library"],
        "features": {
            "shelf": {
                "ambient": True,
                "keywords": ["shelf", "shelves", "gap", "books", "bookshelf", "bookshelves"],
                "looks": [
                    "The dust on a lower shelf is disturbed by a narrow, clean gap where a book was recently removed.",
                    "The gap is still there. Nothing nearby explains where the missing book went.",
                ],
                "clues": [("A book was recently removed from the shelf", 1, None)],
                "friend": "He says he doesn't remember taking a book, and changes the subject.",
            },
            "footsteps": {
                "ambient": True,
                "keywords": ["footsteps", "steps", "sound", "sounds", "ceiling", "overhead", "listen"],
                "looks": [
                    "From somewhere above, a few slow footsteps cross the ceiling. After a pause, the very same footsteps cross it again.",
                    "The footsteps repeat, exactly the same, as though something is replaying.",
                ],
                "clues": [("The same few footsteps repeat overhead", 1, 'echoes')],
                "friend": "He says it is only the house settling, and changes the subject.",
            },
            "photos": {
                "ambient": True,
                "keywords": ["photo", "photos", "picture", "pictures", "frame", "frames"],
                "looks": [
                    "The family photos are blurred and unrecognizable. You can't make out any faces.",
                    "The photos remain blurred. You can't tell who they are.",
                ],
                "clues": [("Family photos on the wall are blurred and unrecognizable", 1, 'past')],
                "friend": "He says the photos are just old and faded.",
            },
            
            "history": {
                "ambient": True,
                "keywords": [
                    "book",
                    "history",
                    "pamphlet",
                    "volume",
                    "reading table",
                    "page",
                    "passage",
                    "text",
                ],
                "takeable": "Library Book",
                "looks": [
                    "The missing book lies open on a reading table: a water-stained local history. One passage tells of the house's first owner, who buried his sister before she was truly gone and died soon after. The house stood empty for years before anyone came.",
                    "The page hasn't changed. The ink is faded, but the passage is still legible.",
                ],
                "clues": [("The house's first owner buried his sister alive and died soon after; the house stood empty for years", 1, None)],

            },
        },
    },
    "Kitchen": {
        "description": (
            "The narrow kitchen is cluttered but familiar. Rain ticks "
            "against a dark window above the sink. You remember this kitchen, as if you had never left."
        ),
        "exits": ["Entrance Hall"],
        "img": "kitchen.jpg",
        "aliases": ["kitchen"],
        "features": {
            "cups": {
                "ambient": True,
                "keywords": ["cup", "cups", "mug", "mugs", "teapot", "kettle", "counter"],
                "looks": [
                    "Two cups wait by the teapot. Then you notice a third at the far end of the table, set out and untouched.",
                    "The third cup hasn't moved. It sits exactly where someone would put it for a guest.",
                ],
                "clues": [("A third cup sits set out at the table, as if someone else were expected", 1, 'present')],
                "friend": "If he notices the player noticing, he glances away and changes the subject.",
            },
            "chair": {
                "ambient": True,
                "keywords": ["chair", "chairs", "table", "seat"],
                "looks": [
                    "One chair at the table is pulled out slightly, as though someone had only just stood up from it.",
                    "The chair stays where it is. The seat is cold.",
                ],
                "clues": [("A kitchen chair is pulled out, as though someone had just stood up", 1, 'present')],
            },
            "food": {
                "ambient": True,
                "keywords": ["food", "plate", "plates", "dish", "dishes"],
                "looks": [
                    "A plate of food sits on the counter, untouched. The smell is faint but familiar.",
                    "The plate of food remains. It is cold, but the smell is still faintly familiar.",
                    "It seems like the food has been sitting there for a while, but it isn't spoiled."
                ],
                "clues": [("A plate of food sits on the counter, untouched", 1, 'present'), ("The food has sat out for ages but has not spoiled", 3, 'present')],
            },
            "calendar": {
                "ambient": True,
                "keywords": ["calendar", "date", "dates"],
                "looks": [
                    "The calendar on the wall is turned to March, but the year is faded and unreadable. It is currently October.",
                ],
                "clues": [("The calendar on the wall is turned to March, but it is currently October. Year is faded and unreadable", 1, 'past')],
            },
        },
    },
    "Grand Staircase": {
        "description": (
            "The staircase groans beneath your weight. At the "
            "landing, a portrait hangs crookedly. From above "
            "comes the faint sound of someone humming."
        ),
        "exits": ["Entrance Hall", "Upper Landing"],
        "img": "staircase.jpg",
        "aliases": ["grand staircase", "staircase", "stairs", "upstairs"],
        "features": {
            "portrait": {
                "ambient": True,
                "keywords": ["portrait", "painting", "picture"],
                "looks": [
                    "The portrait hangs crookedly. The faces are hard to make out in the dim light.",
                    "The portrait is different from before. Something about the faces has shifted, though you can't say what.",
                ],
                "clues": [("The portrait on the landing changed between looks", 2, None)],
                "friend": "He will not look at it.",
            },
            "humming": {
                "ambient": True,
                "keywords": ["humming", "hum", "music", "voice", "melody", "listen"],
                "looks": [
                    "The humming drifts down from above. When you look up, it falters, then starts again from the beginning.",
                    "The same melody, again, from the very beginning.",
                ],
                "clues": [("The humming upstairs falters whenever you listen", 1, 'echoes')],
                "friend": "He seems not to hear it, or says it is only the house.",
            },
        },
    },
    "Upper Landing": {
        "description": (
            "The upper landing is long and narrow, lit by a single grey window. "
            "Every door along it is shut. At the far end, a folded note is taped "
            "to the frame of one door."
        ),
        "exits": ["Grand Staircase", "Parents' Bedroom"],
        "img": "upper_landing.jpg",
        "gated": {"Parents' Bedroom": "door_open"},
        "aliases": ["upper landing", "upstairs landing", "landing", "upper floor", "second floor", "upstairs", "first floor", "second story"],
        "features": {
            "door": {
                "ambient": True,
                "keywords": ["door", "note", "knock", "knocking"],
                "takeable": "Upper Landing Note",
                "looks": [
                    "The parents' bedroom door is shut. The folded note taped to its frame reads, in a careful hand:\n'Do not open\n\nDo not change\n\nI have to keep things as they are.'",
                    "You press your ear to the wood. From inside comes a slow knock, three times. Then nothing.",
                ],
                "clues": [
                    ("A note on the parents' bedroom door reads: do not open; do not change; I have to keep things as they are", 1, "past"),
                    ("Slow knocking comes from inside the locked bedroom", 2, "echoes"),
                ],
                "friend": "He will not come near the door.",
            },
        },
    },
    "Parents' Bedroom": {
        "description": ("The parents' bedroom is cold and perfectly still. Three figures lie together on the bed, turned toward one another, as if asleep. No dust has settled on anything here. The air smells faintly of cold metal."),
        "exits": ["Upper Landing"],
        "img": "bedroom.jpg",
        "aliases": ["parents' bedroom", "parents bedroom", "parent's bedroom", "parents' room",
                    "parents room", "master bedroom", "bedroom"],
        "features": {
            "bed": {
                "keywords": ["bed", "figures", "family", "mother", "father", "sister", "parents"],
                "looks": ["Three figures lie together on the bed, turned toward one another, as if asleep. None of them breathes, and nothing about them has changed at all."],
            },

        },
    },
}

# Fragment progress includes only clues with an assigned fragment kind.
CLUE_FRAGMENT = {
    text: frag
    for room in ROOMS.values()
    for feat in room.get("features", {}).values()
    for (text, _n, frag) in feat.get("clues", [])
    if frag
}
 
# "go back" / "go up" / "go down" shortcuts
BACK = {
    "Library": "Entrance Hall",
    "Kitchen": "Entrance Hall",
    "Grand Staircase": "Entrance Hall",
    "Upper Landing": "Grand Staircase",
    "Parents' Bedroom": "Upper Landing",
}
VERTICAL = {
    ("Entrance Hall", "up"): "Grand Staircase",
    ("Grand Staircase", "up"): "Upper Landing",
    ("Grand Staircase", "down"): "Entrance Hall",
    ("Upper Landing", "down"): "Grand Staircase",
}

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
def new_game():
    return {
        "room": "Entrance Hall",
        "friend_room": "Entrance Hall",
        "inventory": ["The Letter"],
        "clues": [],
        "visited": ["Entrance Hall"],
        "examined": {},          # "Room:feature" -> times examined
        "stage": 0,              # index into prompt.STAGES
        "turns_in_stage": 0,
        "turn_count": 0,
        "room_turns": 0,         # turns spent in the current room since arriving
        "last_notice_turn": -99, # turn_count when a detail was last surfaced
        "last_nudge_turn": -99,  # turn_count when the friend was last nudged
        "nudges_here": 0,          # nudges in this room since last move (escalate)
        "last_sister_turn": -99,
        "sister_warning_count": 0,
        "sister_bargain_available": False,
        "sister_bargain_heard": False,
        "sister_present": False,
        "sister_conversation_turns": 0,
        "denial": 8,             # friend's denial (high = deflecting)
        "pushed": 0,
        "support_given": 0,
        "door_open": False,        # whether the parents' bedroom door is open
        "truth_known": False,       # whether the player has learned the truth about the house
        "final_revelations": [],   # authored family memories shared by the friend
        "sister_seen": False,
        "ending": None,          # None or an ending id
        "last_result": None,     # engine result for the current turn
        "history": [{"role": "assistant", "content": "\"You came. I didn't think you would... Thank you.\"\n\n"}],
        "summary": "",           # rolling summary of folded-away history
        "summary_idx": 0,        # history[:summary_idx] is already summarized
    }

def fragment_progress(game):
    """Return clue counts and completion status for each memory fragment."""
    counts = {kind: 0 for kind in FRAGMENT_KINDS}
    for clue in game["clues"]:
        frag = CLUE_FRAGMENT.get(clue)
        if frag:
            counts[frag] = counts.get(frag, 0) + 1
    return {
        kind: {
            "found": counts[kind],
            "complete": counts[kind] >= FRAGMENT_CLUES_NEEDED,
        }
        for kind in FRAGMENT_KINDS
    }


def fragments_complete(game):
    """Set of completed fragment kinds ('past', 'present', 'echoes')."""
    return {
        kind
        for kind, progress in fragment_progress(game).items()
        if progress["complete"]
    }
 
 
def exit_labels(game, room_name):
    """Exit names for display, marking locked ones."""
    room = ROOMS[room_name]
    gated = room.get("gated", {})
    labels = []
    for e in room["exits"]:
        flag = gated.get(e)
        labels.append(f"{e} (door locked)" if flag and not game[flag] else e)
    return labels

# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
MOVE_VERBS = ["go", "enter", "head", "walk", "move", "step", "climb", "ascend",
              "descend", "return", "run", "visit", "follow", "proceed"]
TAKE_VERBS = ["take", "grab", "pick", "pocket", "steal"]

LEAVE_RE = re.compile(
    r"\b(leave|exit|flee|escape)\b.*\b(house|mansion|manor)\b"
    r"|\bgo outside\b|\bwalk out\b"
)
NEGATION_RE = re.compile(r"\b(not|never|without)\b|n't\b|\bwont\b|\bdont\b")
TOGETHER_RE = re.compile(
    r"\b(leave|go|walk|get out|come|take him|lead him)\b.*\b(together|with me|with him)\b"
    r"|\b(together|with me)\b.*\b(leave|go|out)\b"
    r"|\blet'?s (leave|get out)\b"
)
SISTER_ACCEPT_RE = re.compile(
    r"\b(?:i accept|i agree to (?:your|the) (?:offer|bargain)|"
    r"i choose (?:to accept|your offer|the offer|your bargain|the bargain)|"
    r"i'll do it|i will do it|i want them to stay|"
    r"i want to keep them as they are|i want to preserve them)\b"
)
SISTER_PERSPECTIVE_RE = re.compile(
    r"\b(why|what|how|who|where|when|do you|are you|can you|could you|"
    r"tell me|explain|your (side|belief|perspective))\b|\?"
)

# "look around", "what do I see?", "examine the kitchen" ...
LOOK_AROUND_RE = re.compile(
    r"\b(look|glance|scan|survey|search|explore|examine|inspect|study)\w*\b.*\b(around|about|room|surroundings|area)\b"
    r"|\b(examine|inspect|search|study|explore|look)\w*\b.*\b(kitchen|library|hall|staircase|landing|bedroom)\b"
    r"|\bwhat (do|can) i (see|notice|find)\b|\bnotice anything\b"
)
QUOTED_TEXT_RE = re.compile(r'"[^"]*"|“[^”]*”|‘[^’]*’')
MEMORY_RE = re.compile(
    r"\b(remember|recall|used to|when we were (?:kids|children)|"
    r"back when we|childhood)\b"
)
EXAMINE_RE = re.compile(
    r"\b(examine|inspect|study|look at|check|read|listen to|smell|touch)\b"
)
PHYSICAL_ACTION_RE = re.compile(
    r"\b(?:i\s+)?(?:pat|touch|sit|stand|reach|hold|hug|tap|point|"
    r"turn|open|close|pick|take|walk|step|move|climb|enter|follow)\b"
)
SPEECH_RE = re.compile(
    r"\b(?:i\s+)?(?:say|ask|tell|reply|answer|whisper|speak|call)\b"
    r"|\b(?:ask|tell) (?:him|her|your friend)\b"
)
DOOR_TRY_RE = re.compile(r"\b(open|unlock|force|push|break|kick|try|turn|enter)\b.*\bdoor\b")
DOOR_LOOK_RE = re.compile(r"\b(listen|knock|examine|inspect|look|read|study)\b")
 
CONFRONT_RE = re.compile(r"\b(dead|died|dies|death|corpses?|bodies|body)\b")
FAMILY_RE = re.compile(r"\b(mother|mom|mum|father|dad|sister|parents|family)\b")
SUPPORT_RE = re.compile(
    r"\b(comfort|reassure|hug|not your fault|i'?m here|i am here|here for you|not alone|safe)\b"
    r"|\bit'?s (ok|okay|alright)\b"
    r"|\b(?:we can (?:do (?:it|this)|face (?:it|this)|get through (?:it|this))"
    r"|we(?:'ll| will) face (?:it|this)) together\b"
    r"|\b(?:it'?s|it is) going to be (?:ok|okay|alright)\b"
    r"|\b(?:i want to help|i can help|let me help|i'?d like to help)\b"
    r"|\b(?:take my hand|give me your hand)\b"
)

def _mentions(text, words):
    return any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)


def _find_rooms(text):
    return [name for name, r in ROOMS.items() if _mentions(text, r["aliases"])]


def _remove_inventory_mentions(text, inventory):
    """Keep room names inside carried item names from becoming movement targets."""
    for item in sorted(inventory, key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(item.lower())}\b", " ", text)
    return text


def _find_feature(text, room):
    for name, feat in room.get("features", {}).items():
        if _mentions(text, feat["keywords"]):
            return name, feat
    return None
 
 
def _end(game, ending, detail):
    game["ending"] = ending
    return _result("ending", detail)


def _classify_intent(raw_action, game):
    """Classify what the player is doing so narration responds appropriately."""
    action_text = QUOTED_TEXT_RE.sub("", raw_action).lower()
    action_text = _remove_inventory_mentions(action_text, game["inventory"])
    room = ROOMS[game["room"]]

    if MEMORY_RE.search(raw_action.lower()):
        return "memory"
    if LOOK_AROUND_RE.search(action_text):
        return "exploration"
    if EXAMINE_RE.search(action_text) and _find_feature(action_text, room):
        return "examination"

    has_quoted_speech = bool(QUOTED_TEXT_RE.search(raw_action))
    has_speech = (
        has_quoted_speech
        or bool(SPEECH_RE.search(action_text))
        or bool(SUPPORT_RE.search(action_text))
    )
    has_physical_action = bool(PHYSICAL_ACTION_RE.search(action_text))
    if has_speech and has_physical_action:
        return "action_and_dialogue"
    if has_speech or raw_action.strip().endswith("?"):
        return "dialogue"
    if has_physical_action:
        return "physical_action"
    return "roleplay"


def _result(outcome, detail, new_clue=None, ambient=None, friend=None):
    return {
        "nudge": None,        # gentle push to move on (set by apply_action)
        "outcome": outcome,
        "detail": detail,
        "new_clue": new_clue,
        "ambient": ambient,   # small detail to weave into a quiet turn
        "friend": friend,     # optional hint for how the friend reacts
    }


# ---------------------------------------------------------------------------
# Action resolution
# ---------------------------------------------------------------------------
def _examine(game, room_name, name, feat):
    """Record one examination of a feature. Returns (what they notice, new clue(s) or None)."""
    key = f"{room_name}:{name}"
    n = game["examined"].get(key, 0) + 1
    game["examined"][key] = n
    looks = feat["looks"]
    noticed = looks[min(n - 1, len(looks) - 1)]
    found = []
    for text, on_n, _frag in feat.get("clues", []):
        if n == on_n and text not in game["clues"]:
            game["clues"].append(text)
            found.append(text)
    return noticed, ("; ".join(found) if found else None)


def _next_unnoticed(game, room_name):
    """First ambient feature in this room the player hasn't encountered yet."""
    for name, feat in ROOMS[room_name].get("features", {}).items():
        if feat.get("ambient") and game["examined"].get(f"{room_name}:{name}", 0) == 0:
            return name, feat
    return None

def _unfinished(game, room_name):
    """A room still worth visiting: never visited, or details left to notice."""
    if room_name == "Parents' Bedroom":
        return False
    return room_name not in game["visited"] or _next_unnoticed(game, room_name) is not None
 
 
def _path_to(game, start, goal_fn):
    """Breadth-first search over open exits. Returns the route and goal room."""
    from collections import deque
    seen = {start}
    queue = deque([(start, [])])
    while queue:
        room, path = queue.popleft()
        for nxt in ROOMS[room]["exits"]:
            gate = ROOMS[room].get("gated", {}).get(nxt)
            if (gate and not game[gate]) or nxt in seen:
                continue
            seen.add(nxt)
            route = [*path, nxt]
            if goal_fn(nxt):
                return route, nxt
            queue.append((nxt, route))
    return None


def _path_step(game, start, goal_fn):
    """Return the first room on the shortest open route to a goal."""
    hit = _path_to(game, start, goal_fn)
    return (hit[0][0], hit[1]) if hit else None


def _nudge(game):
    """Hint for steering a lingering player onward. None if there is nowhere to send them."""
    room_name = game["room"]
 
    # Everything found, but the door stays shut because the friend isn't ready.
    if (room_name == "Upper Landing" and not game["door_open"]
            and len(fragments_complete(game)) >= 3):
        return (
            "Everything here has been found, but the friend is not ready for the door. "
            "Let him hesitate, almost speak, and look to the player. Patience and kindness may "
            "help him. Do not open the door."
        )
 
    hit = _path_step(game, room_name, lambda r: _unfinished(game, r))
    if not hit and not game["door_open"] and room_name != "Upper Landing":
        hit = _path_step(game, room_name, lambda r: r == "Upper Landing")
    if not hit:
        return None
    step, target = hit
    where = f"the {step}" + (f", on the way to the {target}" if step != target else "")
 
    level = min(game["nudges_here"] + 1, 3)
    if level == 1:
        return (
            "There is nothing more to find here for now. Let the friend gently suggest moving on, "
            f"toward {where}. The move happens only if the player chooses it."
        )
    if level == 2:
        return (
            "Still nothing new here. Let a faint sound or a change in the light from the direction "
            f"of {where} draw attention that way. Do not say what it is. "
            "The move happens only if the player chooses it."
        )
    return (
        "The player has lingered. Let the friend drift toward the exit that leads to "
        f"{where}, stop there, and look back. The player is still in the {room_name} "
        "until they choose to move."
    )
 

def _try_door(game):
    if game["door_open"]:
        return _result("no_change", "The bedroom door already stands open.")
    if len(fragments_complete(game)) < 3:
        return _door_attempt_with_knocking(
            game,
            _result(
            "blocked",
            "The door will not give. It is not only locked: pushing at it feels like pushing "
            "against something holding its breath. The friend begs the player to leave it. "
            "The player does not yet understand enough to know why it matters.",
            friend="He is frightened and pleads with the player to step away.",
            ),
        )
    if game["denial"] > DOOR_DENIAL_MAX:
        return _door_attempt_with_knocking(
            game,
            _result(
                "blocked",
                "The door stays shut. The friend's hand closes on the player's arm. He is not ready, "
                "and the door will not open until he is.",
                friend="He is trembling and cannot let the player open it yet.",
            ),
        )
    game["door_open"] = True
    return _result(
        "door_opened",
        "The door opens at last, without resistance, as if it had only ever been waiting. "
        "Cold, still air spills out. The friend stands frozen beside the player. "
        "The player has not yet gone in.",
    )


def _record_door_knocking(game):
    door = ROOMS["Upper Landing"]["features"]["door"]
    clue = next(
        text for text, _examination_number, fragment in door["clues"]
        if fragment == "echoes" and "knocking" in text.lower()
    )
    if clue in game["clues"]:
        return None
    game["clues"].append(clue)
    return clue


def _door_attempt_with_knocking(game, result):
    clue = _record_door_knocking(game)
    if clue:
        result["new_clue"] = clue
        result["detail"] += " As the player tests it, three slow knocks answer from within."
    return result


def _confront(game):
    if len(fragments_complete(game)) >= 3:
        game["denial"] = max(0, game["denial"] - 1)
        return _result(
            "no_change",
            "The player says aloud what the evidence points to. This time the friend does not "
            "deny it outright: he wavers, almost admits it, then stops, voice cracking. "
            "Nothing else changes.",
            friend="He is on the edge of breaking.",
        )
    game["pushed"] += 1
    game["denial"] = min(10, game["denial"] + 1)
    if game["pushed"] >= PUSH_LIMIT:
        return _end(
            game, "denial",
            "The player pushed too hard, too soon. The friend shuts down completely.",
        )
    warn = " He is close to shutting down." if game["pushed"] == PUSH_LIMIT - 1 else ""
    return _result(
        "no_change",
        "The player bluntly says the friend's family is dead before having any evidence. "
        "The friend flatly denies it, hurt and frightened, and changes the subject." + warn +
        " Nothing in the house changes.",
    )


def _resolve(game, text):
    intent = _classify_intent(text, game)
    spoken = text                                  # full text, quoted speech included
    text = QUOTED_TEXT_RE.sub("", text).lower()    # actions only: speech can't move or examine things
    room_name = game["room"]
    room = ROOMS[room_name]
    room_parse_text = _remove_inventory_mentions(text, game["inventory"])
    rooms_named = _find_rooms(room_parse_text)
    negated = bool(NEGATION_RE.search(text))
    spoken_negated = bool(NEGATION_RE.search(spoken))

    if (
        game.get("sister_bargain_available")
        and game["friend_room"] != game["room"]
        and not spoken_negated
        and SISTER_ACCEPT_RE.search(spoken)
    ):
        if not game.get("sister_bargain_heard"):
            return _result(
                "blocked",
                "The sister has not explained her bargain yet. The player cannot "
                "accept it before hearing what she believes.",
            )
        return _end(
            game,
            "sisters_bargain",
            "The player accepts the sister's bargain and chooses to leave alone, "
            "carrying her partial account of the family's fate.",
        )

    # --- leaving (irreversible, so be strict) -------------------------------
    # "Let's leave together" is something the player says, so quoted speech counts.
    if game["truth_known"] and not spoken_negated and TOGETHER_RE.search(spoken):
        if game["denial"] >= 3:
            return _result(
                "blocked",
                "The friend is not ready to leave together yet. He has seen the truth "
                "but is still resisting it; do not make him agree or move toward the exit.",
            )
        if len(game.get("final_revelations", [])) < len(FINAL_REVELATIONS):
            return _result(
                "blocked",
                "The friend is not ready to leave together yet. There are still family "
                "memories he has not been able to share; do not make him agree or end "
                "the story now.",
            )
        return _end(
            game,
            "leave_together",
            "The player and the friend choose to leave the house together.",
        )
 
    if LEAVE_RE.search(text) and not negated:
        if room_name == "Entrance Hall":
            return _end(game, "escape_alone", "The player walks out of the house alone.")
        return _result("blocked", "The way out of the house is back through the Entrance Hall.")
    
    # --- the bedroom door -----------------------------------------------------
    if room_name == "Upper Landing" and not negated:
        if DOOR_TRY_RE.search(text) and not DOOR_LOOK_RE.search(text):
            return _try_door(game)
 
    # --- blunt confrontation about the family ---------------------------------
    # Confronting him is also said aloud, so quoted speech counts here too.
    if (not game["truth_known"] and CONFRONT_RE.search(spoken) and FAMILY_RE.search(spoken)):
        return _confront(game)

    # --- movement -----------------------------------------------------------
    if _mentions(text, MOVE_VERBS):
        others = [r for r in rooms_named if r != room_name]
        target = others[0] if others else None
        if not target:
            if re.search(r"\bback\b", text) and room_name in BACK:
                target = BACK[room_name]
            elif re.search(r"\b(up|upstairs)\b", text) and (room_name, "up") in VERTICAL:
                target = VERTICAL[(room_name, "up")]
            elif re.search(r"\b(down|downstairs)\b", text) and (room_name, "down") in VERTICAL:
                target = VERTICAL[(room_name, "down")]
        if target:
            route = _path_to(game, room_name, lambda r: r == target)
            if route:
                path, _ = route
                first_time_rooms = []
                for step in path:
                    if step not in game["visited"]:
                        game["visited"].append(step)
                        first_time_rooms.append(step)
                    if step == "Parents' Bedroom":
                        game["truth_known"] = True
                game["room"] = target
                game["room_turns"] = 0
                game["nudges_here"] = 0
                detail = f"The player moved to the {target}."
                if len(path) > 1:
                    detail += f" They passed through {', '.join(path[:-1])} on the way."
                if first_time_rooms:
                    detail += (
                        f" First visit to: {', '.join(first_time_rooms)}."
                    )
                if game["friend_room"] != target:
                    detail += f" The friend remains in the {game['friend_room']}."
                return _result("moved", detail)
            return _result(
                "blocked",
                f"The {target} cannot be reached from the {room_name}. "
                f"Reachable from here: {', '.join(exit_labels(game, room_name))}.",
            )
        if room_name in rooms_named:
            return _result("no_change", f"The player is already in the {room_name}.")

    # --- taking things ------------------------------------------------------
    found = _find_feature(text, room)
    if found and _mentions(text, TAKE_VERBS):
        name, feat = found
        item = feat.get("takeable")
        if not item:
            return _result("blocked", f"The {name} can't be taken.")
        if item in game["inventory"]:
            return _result("no_change", f"The player already has the {item}.")
        game["inventory"].append(item)
        return _result("picked_up", f"The player picked up the {item}.")

    # --- examining things ---------------------------------------------------
    if found and (
        intent not in {"dialogue", "memory"}
        or EXAMINE_RE.search(text)
        or _mentions(text, TAKE_VERBS)
    ):
        name, feat = found
        noticed, new_clue = _examine(game, room_name, name, feat)
        item = feat.get("takeable")
        if item and item not in game["inventory"]:
            game["inventory"].append(item)
            noticed += f" The {item} is added to the player's inventory."
        return _result(
            "examined",
            f"The player examined the {name}. They notice: {noticed}",
            new_clue,
            friend=feat.get("friend"),
        )

    # --- looking around in general: reveal the next unnoticed detail ---------
    if LOOK_AROUND_RE.search(room_parse_text):
        nxt = _next_unnoticed(game, room_name)
        if nxt:
            name, feat = nxt
            noticed, new_clue = _examine(game, room_name, name, feat)
            return _result(
                "examined",
                f"The player looked around the {room_name}. One thing stands out: {noticed}",
                new_clue,
                friend=feat.get("friend"),
            )
        return _result(
            "examined",
            f"The player looked around the {room_name} again. Nothing new stands out. "
            "Describe only what the room description already says, in a fresh way.",
        )

    # --- everything else: free roleplay --------------------------------------
    return _result(
        "no_change",
        "Nothing the engine tracks changed. Treat the action as ordinary roleplay "
        "(talking, resting, small gestures). Do not add items, clues, or events. "
        f"No room change happens: the player is still in the {room_name}, and nobody "
        f"leads them elsewhere unless they choose an exit ({', '.join(exit_labels(game, room_name))}).",
    )


# ---------------------------------------------------------------------------
# Stage progression: Python decides, the model only narrates the current stage
# ---------------------------------------------------------------------------
# Rule i answers "may we advance from stage i to stage i+1?"
STAGE_RULES = [
    lambda g: g["turns_in_stage"] >= 5 and len(g["visited"]) >= 2,   # 0 arrival
    lambda g: g["turns_in_stage"] >= 5 and len(g["clues"]) >= 1,     # 1 contradictions
    lambda g: g["turns_in_stage"] >= 5 and len(g["clues"]) >= 4,     # 2 paintings
    lambda g: g["turns_in_stage"] >= 5 and len(g["clues"]) >= 7,     # 3 sister's warnings
]


def _advance_stage(game):
    if game["door_open"] and game["stage"] < 5:
        game["stage"] = 5
        game["turns_in_stage"] = 0
        return True
    if game["stage"] >= 4:
        return False
    if STAGE_RULES[game["stage"]](game):
        game["stage"] += 1
        game["turns_in_stage"] = 0
        return True
    return False


def apply_action(game, raw_action):
    """Resolve one player action, update game state, return the engine result."""
    game.setdefault("friend_room", "Entrance Hall")
    game.setdefault("sister_seen", False)
    game.setdefault("last_sister_turn", -99)
    game.setdefault("sister_warning_count", 0)
    game.setdefault("sister_bargain_available", False)
    game.setdefault("sister_bargain_heard", False)
    game.setdefault("sister_present", False)
    game.setdefault("sister_conversation_turns", 0)
    game.setdefault("final_revelations", [])
    text = raw_action.lower()
    intent = _classify_intent(raw_action, game)   # classify before the action can change the room
    sister_appearance_due = (
        not game["sister_seen"]
        or game["turn_count"] + 1 - game["last_sister_turn"] >= SISTER_COOLDOWN
    )
    private_sister_due = (
        game["stage"] >= 3
        and sister_appearance_due
        and not game["ending"]
        and game["sister_warning_count"] >= 2
        and not game["sister_bargain_heard"]
        and game["friend_room"] != game["room"]
    )
    speaking_with_sister = (
        (game["sister_present"] or private_sister_due)
        and intent in {"dialogue", "action_and_dialogue"}
        and not game["ending"]
        and game["friend_room"] != game["room"]
    )
    seen_before = len(game["examined"])           # measured BEFORE resolving, so first looks count as fresh
    result = _resolve(game, text)
    if result["outcome"] == "moved":
        intent = "movement"
        game["sister_present"] = False
    elif result["outcome"] == "picked_up":
        intent = "physical_action"
    elif result["outcome"] == "examined" and intent not in {
        "examination",
        "exploration",
    }:
        intent = "examination"
    result["intent"] = intent
    if (
        intent in {"dialogue", "action_and_dialogue"}
        and not game["ending"]
        and game["friend_room"] != game["room"]
        and not speaking_with_sister
    ):
        game["friend_room"] = game["room"]
        result["friend_arrived"] = True
        result["detail"] += (
            f" The friend joins the player in the {game['room']} so they can speak "
            "face to face."
        )

    game["turn_count"] += 1
    game["turns_in_stage"] += 1
    if result["outcome"] != "moved":
        game["room_turns"] += 1

    # Slow drip: on quiet (no_change) turns, surface one small detail now and then.
    if (
        result["outcome"] == "no_change"
        and not game["ending"]
        and game["room_turns"] >= AMBIENT_AFTER_TURNS
        and game["turn_count"] - game["last_notice_turn"] >= AMBIENT_COOLDOWN
    ):
        nxt = _next_unnoticed(game, game["room"])
        if nxt:
            name, feat = nxt
            noticed, new_clue = _examine(game, game["room"], name, feat)
            result["ambient"] = noticed
            result["new_clue"] = new_clue
            result["friend"] = result["friend"] or feat.get("friend")
 
    # Kindness lowers his guard a little, including after the truth is faced.
    if (
        result["outcome"] == "no_change"
        and not game["ending"]
        and game["support_given"] < SUPPORT_LIMIT
        and SUPPORT_RE.search(text)
    ):
        game["support_given"] += 1
        game["denial"] = max(0, game["denial"] - 1)
        result["friend"] = result["friend"] or "He softens a little at the kindness; his guard lowers for a moment."
 
    # Time runs out if the truth was never faced or the friend remains in denial.
    if (
        not game["ending"]
        and game["turn_count"] >= MAX_TURNS
        and (not game["truth_known"] or game["denial"] >= 3)
    ):
        result = _end(game, "denial", "Too much time has passed. The house closes around the friend.")
 
    # "Fresh" = the player met something new this turn (first look at a feature, or a clue).
    fresh = len(game["examined"]) > seen_before or bool(result["new_clue"])
    if fresh:
        game["last_notice_turn"] = game["turn_count"]
 
    # Nudge: the room is exhausted and the player keeps lingering -> steer them onward.
    if (
        not fresh
        and result["outcome"] in ("no_change", "examined")
        and not game["ending"]
        and not game["truth_known"]
        and game["room_turns"] >= NUDGE_AFTER_TURNS
        and game["turn_count"] - game["last_notice_turn"] >= NUDGE_AFTER_TURNS
        and game["turn_count"] - game["last_nudge_turn"] >= NUDGE_COOLDOWN
        and _next_unnoticed(game, game["room"]) is None
    ):
        nudge = _nudge(game)
        if nudge:
            result["nudge"] = nudge
            game["last_nudge_turn"] = game["turn_count"]
            game["nudges_here"] += 1
 
    if result["new_clue"]:
        for _ in result["new_clue"].split("; "):
            game["denial"] = max(0, game["denial"] - 1)

    if (
        game["truth_known"]
        and game["denial"] < 3
        and game["friend_room"] == game["room"]
        and intent in {"dialogue", "action_and_dialogue"}
        and result["outcome"] not in {"blocked", "ending"}
        and len(game["final_revelations"]) < len(FINAL_REVELATIONS)
    ):
        revelation = FINAL_REVELATIONS[len(game["final_revelations"])]
        game["final_revelations"].append(revelation["id"])
        result["family_memory"] = revelation

    result["stage_advanced"] = _advance_stage(game)
    sister_due = (
        not game["sister_seen"]
        or game["turn_count"] - game["last_sister_turn"] >= SISTER_COOLDOWN
    )
    if game["stage"] >= 3 and sister_due and not game["ending"]:
        can_speak_privately = (
            game["sister_warning_count"] >= 2
            and not game["sister_bargain_heard"]
            and game["friend_room"] != game["room"]
        )
        if can_speak_privately:
            appearance = (
                "The sister appears again, but this time she does not repeat her "
                "warning. With the friend elsewhere, she looks directly at the player "
                "and seems willing to explain why she wants the family left undisturbed."
            )
            game["sister_bargain_available"] = True
            game["sister_present"] = True
            game["sister_conversation_turns"] = 0
        else:
            appearance = (
                "A faint figure resolves into the friend's sister. She appears briefly "
                "and says, 'You shouldn't be here. Please. It's safer if you go.' "
                "Then she is gone."
                if not game["sister_seen"]
                else "The friend's sister appears briefly again and quietly repeats her "
                "warning to leave. Then she is gone."
            )
            game["sister_warning_count"] = min(2, game["sister_warning_count"] + 1)
            game["sister_present"] = False
        game["sister_seen"] = True
        game["last_sister_turn"] = game["turn_count"]
        result["sister"] = appearance
        result["sister_private_encounter"] = can_speak_privately

    if speaking_with_sister and result["outcome"] not in {"ending", "blocked"}:
        result["sister_conversation"] = True
        if SISTER_PERSPECTIVE_RE.search(raw_action.lower()):
            game["sister_bargain_heard"] = True
            result["sister_perspective"] = SISTER_PRESERVATION_MEMORY
        game["sister_conversation_turns"] += 1
        if game["sister_conversation_turns"] >= SISTER_CONVERSATION_LIMIT:
            game["sister_present"] = False
            result["sister_departed"] = True

    game["last_result"] = result
    print("Game state:")
    pprint(game, sort_dicts=False)
    return result