"""engine.py - authoritative game state and rules.

Nothing in here calls the model. The model only ever sees the *result* of
what this module decides (see prompt.py).
"""
import re
from pprint import pprint


# Slow clue drip: during quiet turns the engine surfaces one small detail.
AMBIENT_AFTER_TURNS = 2   # turns spent in a room before a detail may surface
AMBIENT_COOLDOWN = 3      # minimum turns between any two noticed details
FRAGMENT_CLUES_NEEDED = 2  # clues of one kind needed to complete a memory fragment
DOOR_DENIAL_MAX = 3        # friend's denial must be at or below this to open the door
PUSH_LIMIT = 3             # blunt confrontations before the evidence -> he shuts down
SUPPORT_LIMIT = 3          # times kindness can lower his denial
MAX_TURNS = 90             # truth not faced by then -> "denial" ending
NUDGE_AFTER_TURNS = 5
NUDGE_COOLDOWN = 3

# ---------------------------------------------------------------------------
# World data
# ---------------------------------------------------------------------------
# "features" are things the player can examine/take. "looks" is what each
# successive examination reveals (the last entry repeats). "clue" is
# (clue text, examination number on which it is found).
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
        "aliases": ["entrance hall", "entrance", "hallway", "hall", "foyer", "downstairs"],
        "features": {
            "smell": {
                "ambient": True,
                "keywords": ["smell", "scent", "old", "dusty", "odor"],
                "looks": ["A musty smell lingers in the air, a mixture of old wood and dust."],
                "clue": ("A musty smell lingers in the air", 1),
            },
            "clock": {
                "ambient": True,
                "keywords": ["clock", "time", "watch", "tick", "ticking"],
                "looks": [
                    "A tall clock stands against the wall, its hands stopped at a quarter past three. The pendulum hangs perfectly still. The clock hasn't moved. Nothing in this hall ticks.",
                ],
                "clue": ("The clock on the wall is frozen at 3:15", 1),
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
                "keywords": ["shelf", "shelves", "gap", "book", "books", "bookshelf", "bookshelves"],
                "looks": [
                    "The dust on a lower shelf is disturbed by a narrow, clean gap where a book was recently removed.",
                    "The gap is still there. Nothing nearby explains where the missing book went.",
                ],
                "clue": ("A book was recently removed from the shelf", 1),
            },
            "footsteps": {
                "ambient": True,
                "keywords": ["footsteps", "steps", "sound", "sounds", "ceiling", "overhead", "listen"],
                "looks": [
                    "From somewhere above, a few slow footsteps cross the ceiling. After a pause, the very same footsteps cross it again.",
                    "The footsteps repeat, exactly the same, as though something is replaying.",
                ],
                "clue": ("The same few footsteps repeat overhead", 1),
            },
            "photos": {
                "ambient": True,
                "keywords": ["photo", "photos", "picture", "pictures", "frame", "frames"],
                "looks": [
                    "The family photos are blurred and unrecognizable. You can't make out any faces.",
                    "The photos remain blurred. You can't tell who they are.",
                ],
                "clue": ("Family photos on the wall are blurred and unrecognizable", 1),
            },
            
            "history": {
                "ambient": True,
                "keywords": ["book", "history", "pamphlet", "volume", "table", "reading table"],
                "looks": [
                    "The missing book lies open on a reading table: a water-stained local history. One passage tells of the house's first owner, who buried his sister before she was truly gone and died soon after. The house stood empty for years before anyone came.",
                    "The page hasn't changed. The ink is faded, but the passage is still legible.",
                ],
                "clues": [("The house's first owner buried his sister alive and died soon after; the house stood empty for years", 1, None)],
        },
    }
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
                "clue": ("A third cup sits set out at the table, as if someone else were expected", 1),
                "friend": "If he notices the player noticing, he glances away and changes the subject.",
            },
            "chair": {
                "ambient": True,
                "keywords": ["chair", "chairs", "table", "seat"],
                "looks": [
                    "One chair at the table is pulled out slightly, as though someone had only just stood up from it.",
                    "The chair stays where it is. The seat is cold.",
                ],
                "clue": ("A kitchen chair is pulled out, as though someone had just stood up", 1),
            },
            "food": {
                "ambient": True,
                "keywords": ["food", "meal", "dinner", "breakfast", "lunch", "plate", "plates", "dish", "dishes"],
                "looks": [
                    "A plate of food sits on the counter, untouched. The smell is faint but familiar.",
                    "The plate of food remains. It is cold, but the smell is still faintly familiar.",
                    "It seems like the food has been sitting there for a while, but it isn't spoiled."
                ],
                "clue": ("A plate of food sits on the counter, untouched", 1),
            },
            "calendar": {
                "ambient": True,
                "keywords": ["calendar", "date", "month", "day", "year"],
                "looks": [
                    "The calendar on the wall is turned to March, but the year is faded and unreadable. It is currently October.",
                ],
                "clue": ("The calendar on the wall is turned to March, but it is currently October. Year is faded and unreadable", 1),
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
                "clue": ("The portrait on the landing changed between looks", 2),
                "friend": "He will not look at it.",
            },
            "humming": {
                "ambient": True,
                "keywords": ["humming", "hum", "music", "voice", "melody", "listen"],
                "looks": [
                    "The humming drifts down from above. When you look up, it falters, then starts again from the beginning.",
                    "The same melody, again, from the very beginning.",
                ],
                "clue": ("The humming upstairs falters whenever you listen", 1),
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
        "aliases": ["upper landing", "upstairs landing", "landing", "upper floor", "second floor"],
        "features": {
            "door": {
                "ambient": True,
                "keywords": ["door", "note", "knock", "knocking"],
                "looks": [
                    "The parents' bedroom door is shut. The folded note taped to its frame reads, in a careful hand: 'Do not open. Do not change anything.'",
                    "You press your ear to the wood. From inside comes a slow knock, three times. Then nothing.",
                ],
                "clues": [
                    ("A note on the parents' bedroom door reads: do not open, do not change anything", 1, "rules"),
                    ("Slow knocking comes from inside the locked bedroom", 2, "night"),
                ],
                "friend": "He will not come near the door.",
            },
        },
    },
    "Parents' Bedroom": {
        "description": ("The parents' bedroom is cold and perfectly still. Three figures lie together on the bed, turned toward one another, as if asleep. No dust has settled on anything here. The air smells faintly of cold metal."),
        "exits": ["Upper Landing"],
        "img": "bedroom.jpg",
        "aliases": ["parents' bedroom", "bedroom", "parents' room"],
        "features": {
            "bed": {
                "keywords": ["bed", "figures", "family", "mother", "father", "sister", "parents"],
                "looks": ["Three figures lie together on the bed, turned toward one another, as if asleep. None of them breathes, and nothing about them has changed at all."],
            },
        },
    }

}
    
# Which fragment each clue belongs to, built from ROOMS.
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
        "denial": 8,             # friend's denial (high = deflecting)
        "pushed": 0,
        "support_given": 0,
        "door_open": False,        # whether the parents' bedroom door is open
        "truth_known": False,       # whether the player has learned the truth about the house
        "ending": None,          # None or an ending id
        "last_result": None,     # engine result for the current turn
        "history": [{"role": "assistant", "content": "\"You came. I didn't think you would... Thank you.\"\n\n"}],
        "summary": "",           # rolling summary of folded-away history
        "summary_idx": 0,        # history[:summary_idx] is already summarized
    }

def fragments_complete(game):
    """Set of completed fragment kinds ('routine', 'rules', 'night')."""
    counts = {}
    for clue in game["clues"]:
        frag = CLUE_FRAGMENT.get(clue)
        if frag:
            counts[frag] = counts.get(frag, 0) + 1
    return {f for f, n in counts.items() if n >= FRAGMENT_CLUES_NEEDED}
 
 
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

# "look around", "what do I see?", "examine the kitchen" ...
LOOK_AROUND_RE = re.compile(
    r"\b(look|glance|scan|survey|search|explore|examine|inspect|study)\w*\b.*\b(around|about|room|surroundings|area)\b"
    r"|\b(examine|inspect|search|study|explore|look)\w*\b.*\b(kitchen|library|hall|staircase)\b"
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
)

def _mentions(text, words):
    return any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)


def _find_rooms(text):
    return [name for name, r in ROOMS.items() if _mentions(text, r["aliases"])]


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
    room = ROOMS[game["room"]]

    if MEMORY_RE.search(raw_action.lower()):
        return "memory"
    if LOOK_AROUND_RE.search(action_text):
        return "exploration"
    if EXAMINE_RE.search(action_text) and _find_feature(action_text, room):
        return "examination"

    has_quoted_speech = bool(QUOTED_TEXT_RE.search(raw_action))
    has_speech = has_quoted_speech or bool(SPEECH_RE.search(action_text))
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
 
 
def _path_step(game, start, goal_fn):
    """Breadth-first search over open exits. Returns (first step, goal room) or None."""
    from collections import deque
    seen = {start}
    queue = deque([(start, None)])
    while queue:
        room, first = queue.popleft()
        for nxt in ROOMS[room]["exits"]:
            gate = ROOMS[room].get("gated", {}).get(nxt)
            if (gate and not game[gate]) or nxt in seen:
                continue
            seen.add(nxt)
            step = first or nxt
            if goal_fn(nxt):
                return step, nxt
            queue.append((nxt, step))
    return None
 
 
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
        return _result(
            "blocked",
            "The door will not give. It is not only locked: pushing at it feels like pushing "
            "against something holding its breath. The friend begs the player to leave it. "
            "The player does not yet understand enough to know why it matters.",
            friend="He is frightened and pleads with the player to step away.",
        )
    if game["denial"] > DOOR_DENIAL_MAX:
        return _result(
            "blocked",
            "The door stays shut. The friend's hand closes on the player's arm. He is not ready, "
            "and the door will not open until he is.",
            friend="He is trembling and cannot let the player open it yet.",
        )
    game["door_open"] = True
    game["denial"] = min(game["denial"], 2)
    return _result(
        "door_opened",
        "The door opens at last, without resistance, as if it had only ever been waiting. "
        "Cold, still air spills out. The friend stands frozen beside the player. "
        "The player has not yet gone in.",
    )
 
 
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
    text = QUOTED_TEXT_RE.sub("", text).lower()
    room_name = game["room"]
    room = ROOMS[room_name]
    rooms_named = _find_rooms(text)
    negated = bool(NEGATION_RE.search(text))

  # --- leaving (irreversible) -------------------------------
    if game["truth_known"] and not negated and TOGETHER_RE.search(text):
        return _end(game, "leave_together",
                    "The player and the friend choose to leave the house together.")
 
    if LEAVE_RE.search(text) and not negated:
        if room_name == "Entrance Hall":
            return _end(game, "escape_alone", "The player walks out of the house alone.")
        return _result("blocked", "The way out of the house is back through the Entrance Hall.")
    
    # --- the bedroom door -----------------------------------------------------
    if room_name == "Upper Landing" and not negated:
        if DOOR_TRY_RE.search(text) and not DOOR_LOOK_RE.search(text):
            return _try_door(game)
 
    # --- blunt confrontation about the family ---------------------------------
    if (not game["truth_known"] and CONFRONT_RE.search(text) and FAMILY_RE.search(text)):
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
            if target in room["exits"]:
                flag = room.get("gated", {}).get(target)
                if flag and not game[flag]:
                    return _result(
                        "blocked",
                        f"The door to the {target} is shut and locked. It will not simply open; "
                        "the player would have to try the door itself.",
                    )
                first_time = target not in game["visited"]
                game["room"] = target
                game["room_turns"] = 0
                if first_time:
                    game["visited"].append(target)
                if target == "Parents' Bedroom":
                    game["truth_known"] = True
                    game["denial"] = min(game["denial"], 1)
                detail = f"The player moved to the {target}."
                if first_time:
                    detail += " It is their first time in this room."
                return _result("moved", detail)
            return _result(
                "blocked",
                f"The {target} cannot be reached directly from the {room_name}. "
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
        return _result(
            "examined",
            f"The player examined the {name}. They notice: {noticed}",
            new_clue,
            friend=feat.get("friend"),
        )

    # --- looking around in general: reveal the next unnoticed detail ---------
    if LOOK_AROUND_RE.search(text):
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
        f"leads them elsewhere unless they choose an exit ({', '.join(room['exits'])}).",
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
    text = raw_action.lower()
    result = _resolve(game, raw_action.lower())
    intent = _classify_intent(raw_action, game)
    seen_before = len(game["examined"])
    if result["outcome"] == "moved":
        intent = "movement"
    elif result["outcome"] == "picked_up":
        intent = "physical_action"
    elif result["outcome"] == "examined" and intent not in {
        "examination",
        "exploration",
    }:
        intent = "examination"
    result["intent"] = intent

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
 
    # Kindness lowers his guard a little (a few times only).
    if (
        result["outcome"] == "no_change"
        and not game["ending"]
        and not game["truth_known"]
        and game["support_given"] < SUPPORT_LIMIT
        and SUPPORT_RE.search(text)
    ):
        game["support_given"] += 1
        game["denial"] = max(0, game["denial"] - 1)
        result["friend"] = result["friend"] or "He softens a little at the kindness; his guard lowers for a moment."
 
    # Time runs out if the truth was never faced.
    if not game["ending"] and not game["truth_known"] and game["turn_count"] >= MAX_TURNS:
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
    result["stage_advanced"] = _advance_stage(game)
 
    game["last_result"] = result
    return result