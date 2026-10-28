"""prompt.py - builds what the model sees each turn.

Layers (top to bottom):
  1. CORE            static narrator rules            (cacheable prefix)
  2. story block     premise, friend sheet, letter    (static per story)
  3. stage block     what may be revealed *now*       (changes with stage)
  4. state block     room, exits, inventory, clues    (changes per turn)
  5. history         last N messages (older -> summary)
  6. engine result + reminder, attached to the player's latest message
"""
import re

import ollama

CORE = """You are the narrator of a gothic-horror interactive story, "The House That Remembers".

How to write:
- Reply in 2-5 short sentences of grounded, sensory prose. Restrained horror: unsettling details over scares.
- Respond directly to what the player does. Never decide the player's actions, feelings or choices for them.
- Keep dialogue natural and brief. Avoid melodrama, stacked metaphors, repeated descriptions and exposition.
- Quiet, ordinary moments are fine. Not every turn needs a clue or a scare.

Truth rules:
- The ENGINE RESULT attached to the player's message is authoritative. Narrate exactly that. If it says an action failed or nothing changed, narrate that. Do not add items, clues, opened doors or room changes.
- A character may suggest going somewhere, but the move only happens if the player chooses it.
- Only mention shared memories or family details that appear in this prompt or earlier in the conversation. Never invent family history, backstory, or what happened to the family.
- Never explain the supernatural neatly. If asked directly about the past, characters answer in fragments, contradict themselves, or change the subject.
- Do not introduce a warning, apparition, clue or change of location unless the STORY NOW section or the ENGINE RESULT calls for it."""

# The model imitates examples far better than descriptions.
FRIEND_EXAMPLES = """  "You came. I... sorry. You came. Good."
  "I haven't been sleeping much. The house is loud at night."
  "Do you want tea? There's... yes. Tea. I can do that.\""""

# One entry per canon "revelation_order" stage. Index must match engine.STAGE_RULES.
STAGES = [
    {   # 0 - Arrival and uneasy normality
        "now": "The friend is unwell, glad the player came, and wants help but cannot explain. The house is unsettling but nothing is understood yet.",
        "friend": "He tries to act normal and spend ordinary time together. He deflects direct questions about the house. He does not bring up family members on his own.",
        "steer": "Let the player settle in and explore. Uncanny details come only from the engine (ambient details and examined results). Weave those in; do not invent uncanny details of your own.",
    },
    {   # 1 - Contradictions
        "now": "Details about the friend's family do not quite add up.",
        "friend": "He mentions his family casually, in the present tense, as if they are alive and nearby: his mother is resting, his father is busy upstairs, his sister is 'around'. He does not notice anything odd. If asked to see them, or asked directly about them, he answers vaguely and changes the subject.",
        "steer": "Let this come up once or twice in passing, e.g. \"Mum's resting. She hasn't been sleeping well.\" Do not explain it.",
    },
    {   # 2 - Frozen house and family traces
        "now": "The house is frozen in time: clocks are stopped, calendars are out of date, food never spoils, and places are set for people who are not there. Portraits can change between looks. The friend has lost track of time.",
        "friend": "He says time is 'strange' or that he has lost count of the days. He grows uneasy when stopped clocks, old dates or the extra place settings are mentioned and tries to move on.",
        "steer": "Describe frozen or changed details only when the engine provides them. Otherwise keep the house quietly wrong: a sound repeating, a door slightly off.",
    },
    {   # 3 - Sister's warnings
        "now": "A faint figure associated with the sister appears now and then, hums, and warns the player to leave. She is sincere, loving, frightened and mistaken about what is best.",
        "friend": "He does not see her, or insists the player imagined it.",
        "steer": "Her appearances are brief and intermittent: one or two lines at most, then gone. She speaks gently and urgently, e.g. \"You shouldn't be here. Please. It's safer if you go.\" She never threatens. Do not say what happened to the family.",
    },
    {   # 4 - Parents' fragments
        "now": "Slow knocking and footsteps come from behind the locked bedroom door upstairs. They are the parents' lingering fragments: patient, never angry. They want the repeating memory to end.",
        "friend": "He flinches at the knocking and tells the player, \"Whatever you do, don't answer it.\" Fragments of memory slip out, then he retreats.",
        "steer": "Use incomplete echoes and half-heard sounds. Never state what happened to the family. The door itself opens only when the engine says so.",
    },
    {   # 5 - Reconstructed truth
        "now": "The bedroom door has opened. Inside, the family lie preserved as if asleep. The truth, to be revealed only gently and in fragments: after the father and son stopped speaking, the father locked himself, the mother and the sister in this room and told the son never to open the door. Cut off from help and drained by the house, they died inside. The friend knocked once, heard nothing, obeyed the rule out of anger and fear, and never opened it. The house kept the room as it was.",
        "friend": "His denial breaks. He speaks in halting fragments and quiet realization, not speeches. He does not blame the player. He may say he cannot stay here, but never decides for the player.",
        "steer": "Let the moment breathe: stillness, cold, grief. Never describe wounds, decay or gore. The family looks asleep. Do not force the player to leave, stay or forgive.",
    },
]

ENDINGS = {
    "leave_together": (
        "The player and the friend have faced the truth and choose to leave together. "
        "Write the final scene in 4-6 sentences: the friend's grief and fragile steadiness, the house letting go "
        "(the stopped clocks may tick once; the knocking and humming fall silent), the door, the rain easing. "
        "No gore. Offer no further choices. End the story."
    ),
    "escape_alone": (
        "The player has chosen to leave the house alone, and the engine confirms it. "
        "Write the final scene in 4-6 sentences: the door, the rain, the friend's reaction according to his condition, "
        "the house behind them. Do not explain what happened to the family. Offer no further choices. End the story."
    ),
    "denial": (
        "The friend could not face it. He refuses help and withdraws, insisting everyone is only resting. "
        "Write the final scene in 4-6 sentences: the player cannot reach him, the house settles around him, "
        "the knocking and humming resume as though nothing happened, and he is left with the house. "
        "Do not describe the family or explain what happened. Offer no further choices. End the story."
    ),
}


def denial_band(denial):
    if denial >= 7:
        return "high denial: he insists things are fine, deflects, changes the subject"
    if denial >= 4:
        return "wavering: he pauses, almost admits things, then retreats"
    return "cracking: fragments of memory slip out and he is visibly shaken"


def story_block(canon):
    f = canon["character_dynamics"]["friend"]
    return (
        "STORY PREMISE\n"
        f"{canon['premise']['summary']}\n\n"
        "THE FRIEND (signs his letter 'E.')\n"
        f"- Condition: {f['initial_state']}\n"
        f"- Personality: {f['personality']}\n"
        f"- Voice: {f['voice']}\n"
        f"- Early behavior: {f['early_behavior']}\n"
        "- Example lines (for tone only; do not repeat them verbatim):\n"
        f"{FRIEND_EXAMPLES}\n\n"
        "THE LETTER HE SENT\n"
        f"{canon['opening']['letter_text']}"
    )


def stage_block(game):
    if game["ending"]:
        text = ENDINGS[game["ending"]]
        if game["ending"] == "escape_alone":
            text += (
                " The player saw the truth in the bedroom before leaving; the friend stays behind with his family."
                if game["truth_known"]
                else " The player never learned what was upstairs; the friend stays behind in the house."
            )
        return "ENDING\n" + text
    s = STAGES[game["stage"]]
    return (
        f"STORY NOW: {s['now']}\n"
        f"FRIEND RIGHT NOW: {s['friend']}\n"
        f"FRIEND'S CONDITION: {denial_band(game['denial'])}\n"
        f"STEER TOWARD (gently, never force): {s['steer']}\n"
        f"Turns spent in this part of the story: {game['turns_in_stage']}"
    )


def state_block(game):
    from engine import ROOMS, exit_labels  # local import avoids a cycle if engine grows

    room = ROOMS[game["room"]]
    lines = [
        "CURRENT STATE",
        f"Room: {game['room']}",
        f"Room description: {room['description'].strip()}",
        f"Exits: {', '.join(exit_labels(game, game['room']))}",
        f"Inventory: {', '.join(game['inventory']) or 'empty'}",
        f"Clues the player has found: {', '.join(game['clues']) or 'none'}",
        "Established player memories: childhood companions; playing outside together; "
        "helping the friend with kitchen chores; exploring the family library; "
        "sleeping over in the guest room.",
    ]
    if game["summary"]:
        lines.append(f"Earlier in the story: {game['summary']}")
    return "\n".join(lines)


def _engine_note(game):
    r = game["last_result"]
    if not r:
        return ""
    note = (
        "\n\n[ENGINE RESULT - authoritative]\n"
        f"Player intent: {r.get('intent', 'roleplay')}\n"
        f"Outcome: {r['outcome']}\n"
        f"Detail: {r['detail']}"
    )
    if r.get("ambient"):
        note += (
            "\nAmbient detail to weave into this turn in one quiet sentence, "
            f"without making it a big moment: {r['ambient']}"
        )
    if r.get("nudge"):
        note += f"\nGentle push to move the story on (weave in naturally, never force): {r['nudge']}"
    if r["new_clue"]:
        note += f"\nNew clue found: {r['new_clue']}"
    if r.get("friend"):
        note += f"\nFriend's likely reaction (optional): {r['friend']}"
    intent_reminders = {
        "dialogue": (
            "Treat the player's words as spoken to the friend and answer them directly in his "
            "natural, restrained voice. Do not turn the player's words into narration."
        ),
        "memory": (
            "Answer the player's memory question as their character, using only the established "
            "player memories in CURRENT STATE or facts already established in conversation. "
            "Do not invent a specific shared event or reveal hidden family history."
        ),
        "physical_action": (
            "Treat this as a physical action by the player. Acknowledge what they actually did "
            "and the friend's plausible, restrained response; do not invent additional player actions."
        ),
        "action_and_dialogue": (
            "Preserve both parts of the player's input: acknowledge their physical action and "
            "have the friend respond to their spoken words. Do not add actions for the player."
        ),
        "examination": (
            "Treat this as an examination. Use the ENGINE RESULT as the only new observation; "
            "do not add clues or details."
        ),
        "exploration": (
            "Treat this as looking around or exploring. Use only the room description and "
            "ENGINE RESULT for observations; do not add clues or details."
        ),
        "movement": "Narrate the confirmed move into the destination room.",
        "roleplay": "Respond naturally to the player's action without inventing consequential events.",
    }
    reminder = (
        f"{intent_reminders.get(r.get('intent', 'roleplay'), intent_reminders['roleplay'])} "
        "Stay in character. 2-5 short sentences. Add no other items, clues, uncanny events, "
        "room changes or backstory."
    )
    if game["ending"]:
        reminder = "This is the final scene. 4-6 sentences. Close the story."
    return note + f"\n[REMINDER] {reminder}"


def build_messages(game, canon):
    system = "\n\n".join([CORE, story_block(canon), stage_block(game), state_block(game)])
    live = [dict(m) for m in game["history"][game["summary_idx"]:]]
    if live and live[-1]["role"] == "user":
        live[-1]["content"] += _engine_note(game)
    return [{"role": "system", "content": system}, *live]


def generation_options(game):
    return {
        "temperature": 0.6,
        "num_ctx": 8192,
        "num_predict": 320 if game["ending"] else 200,
        "repeat_penalty": 1.1,
    }


def tidy(text):
    """Strip leaked tags and trim a reply cut off mid-sentence."""
    text = re.split(r"\[(?:ENGINE|REMINDER)", text)[0].strip()
    if text and text[-1] not in '.!?"\u201d*_\u2026':
        cut = max(text.rfind(c) for c in ".!?")
        if cut > len(text) * 0.4:
            text = text[: cut + 1]
    return text


# ---------------------------------------------------------------------------
# Rolling summary: fold old history into a few sentences
# ---------------------------------------------------------------------------
SUMMARY_TRIGGER = 20   # live messages before we fold
KEEP_RECENT = 10       # messages kept verbatim after folding


def maybe_summarize(game, model):
    live = game["history"][game["summary_idx"]:]
    if len(live) <= SUMMARY_TRIGGER:
        return
    fold = live[:-KEEP_RECENT]
    transcript = "\n".join(
        f"{'Player' if m['role'] == 'user' else 'Narrator'}: {m['content']}" for m in fold
    )
    prompt = (
        "Summarize the story so far in 3-4 sentences, past tense. "
        "Include only facts stated below: where the player went, what they found, "
        "what was said. Add nothing new and do not solve any mystery.\n\n"
        f"Previous summary: {game['summary'] or '(none)'}\n\n"
        f"New events:\n{transcript}"
    )
    r = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        think=False,
        options={"temperature": 0.2, "num_predict": 200, "num_ctx": 8192},
    )
    summary = r.message.content.strip()
    if summary:
        game["summary"] = summary
        game["summary_idx"] += len(fold)