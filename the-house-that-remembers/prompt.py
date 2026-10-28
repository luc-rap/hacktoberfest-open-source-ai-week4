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

Friend conversation:
- Keep conversational continuity at every story stage: respond to the player's latest statement or request, and follow through on an offer the player accepts before introducing another topic.
- Before the bedroom truth is faced, use gentle small talk or ask about the player's life during natural pauses, not over an unanswered request or immediate action. Once the player has entered the bedroom and learned the truth, do not initiate small talk or pivot to ordinary topics.
- Draw on established shared memories when relevant. Vary topics and avoid repeating the same offer or line.
- Make suggestions purposeful and responsive to the conversation, not a menu of rooms or activities. If tea, a drink, or something warm comes up, naturally suggest the kitchen; do not suggest going upstairs unless the player or story gives a reason.

Truth rules:
- The ENGINE RESULT attached to the player's message is authoritative. Narrate exactly that. If it says an action failed or nothing changed, narrate that. Do not add items, clues, opened doors or room changes. If it supplies a family memory, include that fact clearly in the friend's reply; do not replace it with a vague evasion.
- A character may suggest going somewhere, but the move only happens if the player chooses it.
- The friend's location in CURRENT STATE is authoritative. Never have him hear or answer from another room. If the player starts a conversation while they are apart, the ENGINE RESULT normally brings him into the player's room; narrate that arrival before his reply. The exception is an ENGINE RESULT-marked private sister conversation: answer as the sister and keep the friend elsewhere.
- Only mention shared memories or family details that appear in this prompt or earlier in the conversation. Never invent family history, backstory, or what happened to the family.
- When an ENGINE RESULT reveals readable text or a historical clue, state its important content plainly. The library's account of an earlier owner is separate from the friend's family history and is not a forbidden reveal.
- Never explain the supernatural neatly. Before the bedroom truth is faced, characters may answer questions about the past in fragments, contradict themselves, or change the subject. After the player faces the truth, the friend's response depends on his denial: if he is still resisting, he may minimize or struggle to answer; as his denial falls, he should acknowledge the established facts honestly in brief, halting fragments rather than a speech.
- The sister's appearances stay focused on her warning that the player should leave. Do not have her suggest rooms, activities, or casual conversation. During an ENGINE RESULT-authorized private conversation, she may explain her belief that preserving the family keeps them alive and discuss her bargain, but keep the exchange focused on that belief and warning. This is her perspective, not objective proof that the family is alive, and does not reveal the full truth. These sister-specific limits override the general suggestion and small-talk guidance.
- Do not introduce a warning, apparition, clue or change of location unless the STORY NOW section or the ENGINE RESULT calls for it."""

# The model imitates examples far better than descriptions.
FRIEND_EXAMPLES = """  "You came. I... sorry. You came. Good."
  "Do you remember how we used to help in the kitchen? I was never much good at it."
  "It's strange being back in the library. We used to spend whole afternoons in here."
  "I haven't been sleeping much. The house is loud at night."
  "Tea sounds good. The kitchen's just this way, if you'd like."
  "I miss the old days. Now, everything is so... different. I don't know how to explain it."
  "I just wanted to see you. I haven't had anyone to talk to in a long time."
  "I am glad you came. I don't know how to say it, but I need someone here. I can't be alone."
  "I know we haven't seen each other in years, but it's good to have you here."
  "What about your... family?"
  "How was the trip here? I hope the rain didn't make it too difficult."
  "We used to spend a lot of time in the library"
  "What have you been doing all these years? I mean... if you want to tell me.\""""

# One entry per canon "revelation_order" stage. Index must match engine.STAGE_RULES.
STAGES = [
    {   # 0 - Arrival and uneasy normality
        "now": "The friend is unwell, glad the player came, and wants help but cannot explain. The house is unsettling but nothing is understood yet. Friend invited the player to the house because he is lonely and the history of the house is weighing on him. He is not aware of the truth, but he doesn't want to be alone.",
        "friend": "He tries to act normal and spend ordinary time together. He can ask about the player's life or mention an established childhood memory. He deflects direct questions about the house and does not bring up family members on his own.",
        "steer": "Let the player settle in and explore. Keep the friend's suggestions tied to what the player just said; if tea or a drink is wanted, the kitchen is the natural next step. Do not offer upstairs or list destinations without a reason. When the friend invites the player somewhere, make the destination clear and wait for the player's choice; do not move them automatically. Uncanny details come only from the engine (ambient details and examined results). Weave those in; do not invent uncanny details of your own.",
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
        "now": "The sister's first appearance is authorized when the ENGINE RESULT supplies it; after that she may appear intermittently only when the engine calls for it. She hums and warns the player to leave. She is sincere, loving, frightened and mistaken about what is best.",
        "friend": "He does not see her, or insists the player imagined it.",
        "steer": "When the ENGINE RESULT calls for her, her appearance is brief: one or two lines at most. She speaks gently and urgently, keeping focus on warning the player to leave. She never threatens, suggests going to another room, or starts casual conversation. If the ENGINE RESULT authorizes a private conversation, she may explain that she believes preserving the family keeps them alive and discuss her bargain; present this as her belief, not as confirmed fact. Otherwise do not say what happened to the friend's family.",
    },
    {   # 4 - Parents' fragments
        "now": "Slow knocking and footsteps come from behind the locked bedroom door upstairs. They are the parents' lingering fragments: patient, never angry. They want the repeating memory to end.",
        "friend": "He flinches at the knocking and tells the player, \"Whatever you do, don't answer it.\" Fragments of memory slip out, then he retreats.",
        "steer": "Use incomplete echoes and half-heard sounds. Never state what happened to the friend's family. The door itself opens only when the engine says so.",
    },
    {   # 5 - Reconstructed truth
        "now": "The bedroom door has opened. The family inside are preserved as if asleep. The player faces the truth on entering; the friend can only share the family story as the engine authorizes each memory.",
        "friend": "His denial breaks only as he becomes ready. He speaks in halting fragments and quiet realization, not speeches. If denial is still 3 or higher, he resists and cannot share the next family memory. When denial falls below 3, the ENGINE RESULT may supply one authored family memory; include it honestly and clearly, without adding facts. After the player has entered and learned the truth, keep his conversation focused on the family, his grief, the player's immediate response, and whether to stay or leave. Do not initiate small talk, ask what the player has been doing, bring up unrelated childhood memories, or pivot to ordinary topics. He does not blame the player. He never agrees to leave together unless the engine ends the story.",
        "steer": "If the player has not entered the bedroom, let them choose whether to go in; do not reveal what happened yet. Once the truth is faced, the friend shares the mother's decline, the father's choice, the sister's hope, and his own silence one memory at a time when the ENGINE RESULT supplies each. Let the moment breathe between disclosures without filling pauses with small talk. Never describe wounds, decay or gore. The family looks asleep. Do not force the player to leave, stay or forgive.",
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
    "sisters_bargain": (
        "The player accepts the sister's bargain and leaves alone. The sister's account is her belief that "
        "preserving the family exactly as they are keeps them alive, not objective confirmation. Write a quiet, "
        "unsettling final scene in 4-6 sentences: the player leaves the house alone, carrying the sister's "
        "perspective, while the friend and the family remain in the house. Do not erase or contradict anything "
        "the player already learned or saw, and do not imply that the family was truly saved. Offer no further "
        "choices. End the story."
    ),
}


def denial_band(denial):
    if denial >= 7:
        return "high denial: he insists things are fine, deflects, changes the subject"
    if denial >= 3:
        return "wavering: he pauses, almost admits things, then retreats"
    return "cracking: fragments of memory slip out and he is visibly shaken"


def story_block(canon):
    f = canon["character_dynamics"]["friend"]
    return (
        "STORY PREMISE\n"
        f"{canon['premise']['summary']}\n\n"
        "THE FRIEND (his name is not established; the letter is signed with the initial 'E.')\n"
        "- Refer to him as 'your friend' or 'he'; do not call him 'E.' as though that were his name.\n"
        f"- Condition: {f['initial_state']}\n"
        f"- Personality: {f['personality']}\n"
        f"- Voice: {f['voice']}\n"
        f"- Early behavior: {f['early_behavior']}\n"
        "- Early-story example lines (for tone only; do not repeat them verbatim or use them after the truth is faced):\n"
        f"{FRIEND_EXAMPLES}\n\n"
        "THE LETTER HE SENT\n"
        f"{canon['opening']['letter_text']}"
    )


def stage_block(game):
    if game["ending"]:
        text = ENDINGS[game["ending"]]
        if game["ending"] == "sisters_bargain":
            text += (
                " The player has already entered the bedroom and seen the family."
                if game.get("truth_known")
                else " The player accepted before entering the bedroom and has not seen the family."
            )
        if game["ending"] == "escape_alone":
            text += (
                " The player saw the truth in the bedroom before leaving; the friend stays behind with his family."
                if game["truth_known"]
                else " The player never learned what was upstairs; the friend stays behind in the house."
            )
        return "ENDING\n" + text
    s = STAGES[game["stage"]]
    truth_permission = ""
    if game["stage"] == 5:
        from engine import FINAL_REVELATIONS

        if not game.get("truth_known"):
            truth_permission = (
                "\nTRUTH STATUS: The bedroom door is open, but the player has not entered "
                "and has not faced the truth. Do not reveal the family's fate yet."
            )
        elif game["denial"] >= 3:
            truth_permission = (
                "\nTRUTH STATUS: The player has seen the truth, but the friend is still "
                "resisting it. He may deny or minimize it and cannot yet give a clear account. "
                "Do not force acceptance; let sincere support soften him. If his denial remains "
                "unresolved, the story can end with him unable to face it."
            )
        elif len(game.get("final_revelations", [])) < len(FINAL_REVELATIONS):
            truth_permission = (
                "\nTRUTH STATUS: The player has seen the family. The friend is ready to "
                "share the story gradually, but has only disclosed the memories recorded "
                "in CURRENT STATE so far. Do not reveal any later family memory unless "
                "the ENGINE RESULT supplies it this turn."
            )
        else:
            truth_permission = (
                "\nTRUTH STATUS: The player has seen the truth and the friend has shared "
                "all four family memories recorded in CURRENT STATE. He can now speak "
                "honestly about what happened. Keep his voice gentle and halting, not a speech."
            )
        if game.get("truth_known"):
            truth_permission += (
                "\nCONVERSATION FOCUS: Do not initiate small talk, ask about the player's "
                "life, or shift to ordinary topics. Keep the exchange with the friend "
                "focused on the family, grief, and the player's immediate choices."
            )
    return (
        f"STORY NOW: {s['now']}\n"
        f"FRIEND RIGHT NOW: {s['friend']}\n"
        f"FRIEND'S CONDITION: {denial_band(game['denial'])}\n"
        f"STEER TOWARD (gently, never force): {s['steer']}\n"
        f"{truth_permission}\n"
        f"Turns spent in this part of the story: {game['turns_in_stage']}"
    )


def state_block(game):
    from engine import FINAL_REVELATIONS, ROOMS, SISTER_PRESERVATION_MEMORY, exit_labels

    room = ROOMS[game["room"]]
    friend_room = game.get("friend_room", "Entrance Hall")
    lines = [
        "CURRENT STATE",
        f"Room: {game['room']}",
        f"Room description: {room['description'].strip()}",
        f"Truth faced: {'yes' if game.get('truth_known') else 'no'}",
        f"Friend's denial: {game['denial']}/10",
        f"Family memories shared: {len(game.get('final_revelations', []))}/4",
        f"Shared family memories: {', '.join(game.get('final_revelations', [])) or 'none'}",
        f"Sister's private conversation available: {'yes' if game.get('sister_bargain_available') else 'no'}",
        f"Sister's preservation belief heard: {'yes' if game.get('sister_bargain_heard') else 'no'}",
        f"Sister physically present: {'yes' if game.get('sister_present') else 'no'}",
        f"Sister conversation turns: {game.get('sister_conversation_turns', 0)}/5",
        f"Exits: {', '.join(exit_labels(game, game['room']))}",
        (
            "Friend location: with the player in this room."
            if friend_room == game["room"]
            else f"Friend location: {friend_room}. He is not with the player and cannot hear them."
        ),
        f"Inventory: {', '.join(game['inventory']) or 'empty'}",
        f"Clues the player has found: {', '.join(game['clues']) or 'none'}",
        "Established player memories: childhood companions; playing outside together; "
        "helping the friend with kitchen chores; exploring the family library; "
        "sleeping over in the guest room.",
    ]
    if game["summary"]:
        lines.append(f"Earlier in the story: {game['summary']}")
    shared_revelations = set(game.get("final_revelations", []))
    lines.extend(
        f"Family memory already shared ({memory['title']}): {memory['detail']}"
        for memory in FINAL_REVELATIONS
        if memory["id"] in shared_revelations
    )
    if game.get("sister_bargain_heard"):
        lines.append(f"Sister's revealed perspective: {SISTER_PRESERVATION_MEMORY}")
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
    friend_is_here = game.get("friend_room", "Entrance Hall") == game["room"]
    if r.get("friend") and friend_is_here:
        note += f"\nFriend's likely reaction (optional): {r['friend']}"
    if r.get("sister"):
        note += f"\nSister's appearance to narrate this turn: {r['sister']}"
    if r.get("sister_private_encounter"):
        note += (
            "\nThis is the sister's private conversation opportunity, available because "
            "she has already warned the player twice and the friend is elsewhere. "
            "The player may speak with her even if the bedroom door is still closed."
        )
    if r.get("sister_conversation"):
        note += (
            "\nThe player is speaking privately with the sister. Respond as the sister, "
            "not the friend. The friend is elsewhere and must not answer or arrive."
        )
    if r.get("sister_departed"):
        note += (
            "\nAfter this reply, the sister vanishes. Her bargain remains an available "
            "choice if she has explained her perspective; the player may also move or leave normally."
        )
    if r.get("sister_perspective"):
        note += (
            "\nThe sister's perspective to explain clearly if the player asked: "
            f"{r['sister_perspective']}"
        )
    if r.get("family_memory"):
        memory = r["family_memory"]
        note += (
            f"\nFamily memory to acknowledge clearly in the friend's reply "
            f"({memory['title']}): {memory['detail']}"
        )
    if r.get("friend_arrived"):
        note += "\nThe friend has joined the player to speak face to face; narrate his arrival before his response."
    intent_reminders = {
        "dialogue": (
            "Treat the player's words as spoken to the friend and answer directly in his natural, "
            "restrained voice. If the ENGINE RESULT says he joined the player, narrate his arrival "
            "before the reply."
        ),
        "memory": (
            "Answer the player's memory question as their character, using only the established "
            "player memories in CURRENT STATE or facts already established in conversation. "
            "Do not invent a specific shared event or reveal hidden family history."
        ),
        "physical_action": (
            "Treat this as a physical action by the player. Acknowledge what they actually did "
            "and, only if he is in this room, the friend's restrained response. Do not invent "
            "additional player actions."
        ),
        "action_and_dialogue": (
            "Preserve both parts of the player's input: acknowledge their physical action and "
            "have the friend respond. If the ENGINE RESULT says he joined the player, narrate his "
            "arrival before the reply. Do not add actions for the player."
        ),
        "examination": (
            "Treat this as an examination. Use the ENGINE RESULT as the only new observation; "
            "do not add clues or details."
        ),
        "exploration": (
            "Treat this as looking around or exploring. Use only the room description and "
            "ENGINE RESULT for observations; do not add clues or details."
        ),
        "movement": "Narrate the confirmed route and destination. Keep the friend at the location given in CURRENT STATE unless the ENGINE RESULT says he accompanied the player.",
        "roleplay": "Respond naturally to the player's action without inventing consequential events.",
    }
    reminder = (
        f"{intent_reminders.get(r.get('intent', 'roleplay'), intent_reminders['roleplay'])} "
        "Stay in character. 2-5 short sentences. Add no other items, clues, uncanny events, "
        "room changes or backstory."
    )
    if r.get("sister_conversation"):
        reminder = (
            "Answer as the sister, directly to the player. The friend is elsewhere; do not "
            "bring him into the room or let him answer. Stay within the sister's established "
            "beliefs and the engine-authorized perspective."
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