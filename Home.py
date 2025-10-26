
import streamlit as st
import google.generativeai as genai
import webbrowser
import re
import json

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="Physiotherapist Chatbot", page_icon="💬", layout="centered")

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]   # <-- replace with your key
genai.configure(api_key=GOOGLE_API_KEY)

# ==============================
# STATE INIT
# ==============================
defaults = {
    "messages": [{"role": "bot", "content": "Hi there! What pain are you facing today?"}],
    "step": 1,
    "pain_area": "",          # "lower back", "upper back", "shoulder", ...
    "raw_pain_text": "",
    "awaiting_back_region": False,  # if user said generic "back", ask upper/lower
    "asked_clarify_pain": False,    # only re-ask once if pain unclear
    "history": "",
    "asked_clarify_stage": False,   # asked once via follow-up message
    "awaiting_stage_choice": False, # show explicit radio choice if still unclear
    "mode": "",                     # 'stretch' or 'strength'
    "exercise_name": "",
    "reasoning": "",
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ==============================
# STYLE (high-contrast for dark & light)
# ==============================
st.markdown("""
<style>
.chat-bubble { border-radius: 14px; padding: 10px 14px; margin: 6px 0; max-width: 80%; line-height: 1.45; }
.user { background: #2563eb; color: #ffffff; margin-left: auto; }
.bot  { background: #2f3136; color: #e5e7eb; margin-right: auto; }
@media (prefers-color-scheme: light) {
  .bot { background: #eeeeee; color: #222; }
  .user { background: #2563eb; color: #fff; }
}
.chat-container { display: flex; flex-direction: column; }
</style>
""", unsafe_allow_html=True)

# ==============================
# HELPERS
# ==============================
KNOWN_AREAS = [
    "lower back","low back","upper back","back","shoulder","knee","neck","hip","ankle",
    "elbow","wrist","hamstring","quad","calf","glute","groin"
]

def header_pain_text(pain_raw: str) -> str:
    if not pain_raw:
        return "your pain"
    p = pain_raw.strip().lower()
    if "pain" not in p:
        p += " pain"
    return p[0].upper() + p[1:]

def normalize_pain_area(text: str) -> str:
    t = (text or "").lower()
    if any(x in t for x in ["lower back","low back","lower-back"]):
        return "lower back"
    if "upper back" in t or "upper-back" in t:
        return "upper back"
    if "back" in t:
        return "back"  # generic; we will ask upper/lower
    for area in KNOWN_AREAS:
        if area in t:
            return area
    m = re.search(r"(lower back|upper back|back|shoulder|knee|neck|hip|ankle|elbow|wrist|hamstring|quad|calf|glute|groin)", t)
    return m.group(1) if m else ""

def classify_mode(history_text: str) -> str:
    t = (history_text or "").lower()
    strength_triggers = ["late", "advanced", "strength", "strengthening", "building", "stable", "improving", "finished", "completed", "progress"]
    stretch_triggers  = ["early", "beginner", "just started", "still in pain", "sore", "acute", "flare", "tender", "recent", "physio", "rehab", "recovery"]
    if any(k in t for k in strength_triggers):
        return "strength"
    if any(k in t for k in stretch_triggers):
        return "stretch"
    return ""

def ask_gemini_free(prompt: str) -> str:
    model = genai.GenerativeModel("gemini-1.5-flash")
    try:
        return model.generate_content(prompt).text.strip()
    except Exception as e:
        st.error(f"Gemini error: {e}")
        return ""

def gemini_pick_exercise(pain_area: str, mode: str) -> tuple[str, str]:
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""
You are a physiotherapist. The user has '{pain_area}' pain and should focus on '{mode}' work.
Recommend exactly ONE specific exercise name (short, proper name) and a one-sentence reason.
Return STRICT JSON with keys "exercise" and "why".
Example:
{{"exercise":"Pendulum Stretch","why":"It gently mobilizes the shoulder without loading it."}}
"""
    try:
        resp = model.generate_content(prompt).text.strip()
        m = re.search(r"\{.*\}", resp, re.DOTALL)
        data = json.loads(m.group(0)) if m else {}
        ex = (data.get("exercise") or "").strip()
        why = (data.get("why") or "").strip()
        if ex:
            return ex, (why or "This suits your current stage.")
    except Exception:
        pass
    fallback = {
        "upper back": {"stretch": "Squat", "strength": "Squat"},
        "shoulder":   {"stretch": "Squat", "strength": "Squat"},
        "knee":       {"stretch": "Squat", "strength": "Squat"},
        "neck":       {"stretch": "Squat", "strength": "Squat"},
        "hip":        {"stretch": "Leg Raises", "strength": "Squat"},
    }
    bank = fallback.get(pain_area, {"stretch": "Squat", "strength": "Squat"})
    return bank[mode], "This matches your stage and targets the area safely."

# ==============================
# HEADER
# ==============================
st.title("PhysioPal Chatbot")
st.markdown(f"Let's figure out {header_pain_text(st.session_state.pain_area)} and get you the right exercise!", unsafe_allow_html=True)

# ==============================
# CHAT UI
# ==============================
def render_chat():
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for m in st.session_state.messages:
        cls = "user" if m["role"] == "user" else "bot"
        st.markdown(f'<div class="chat-bubble {cls}">{m["content"]}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

render_chat()

# ==============================
# FLOW
# ==============================

# STEP 1 — PAIN AREA (and possibly ask upper/lower)
if st.session_state.step == 1:
    user = st.text_input("You:", key="pain_input", placeholder="e.g. lower back pain, shoulder pain…")
    if st.button("Send"):
        user = user.strip()
        if not user:
            st.stop()
        st.session_state.messages.append({"role": "user", "content": user})
        st.session_state.raw_pain_text = user

        # If we're waiting for upper/lower clarification, handle that first
        if st.session_state.awaiting_back_region:
            lower = "lower" in user.lower()
            upper = "upper" in user.lower()
            if lower:
                st.session_state.pain_area = "lower back"
            elif upper:
                st.session_state.pain_area = "upper back"
            else:
                if not st.session_state.asked_clarify_pain:
                    st.session_state.asked_clarify_pain = True
                    st.session_state.messages.append({"role": "bot", "content": "Please confirm: upper back or lower back?"})
                    st.rerun()
                st.session_state.pain_area = "lower back"
            st.session_state.awaiting_back_region = False
            st.session_state.messages.append({
                "role": "bot",
                "content": "Got it — you mentioned lower back pain. What stage are you in right now (early stages of pain and soreness, or late rehab and strengthening)?",
            })
            st.session_state.step = 2
            st.rerun()

        # Normal first-time parsing
        area = normalize_pain_area(user)
        if not area:
            # one re-ask, then let Gemini try, otherwise default to lower back
            if not st.session_state.asked_clarify_pain:
                st.session_state.asked_clarify_pain = True
                st.session_state.messages.append({"role": "bot", "content": "I didn't catch that. Could you say the body area (e.g., lower back, shoulder, knee)?"})
                st.rerun()
            ai = ask_gemini_free(f"The user wrote: '{user}'. Identify only the body area in 1-2 words (like 'lower back', 'shoulder').")
            area = normalize_pain_area(ai) or "lower back"

        if area == "back":
            st.session_state.awaiting_back_region = True
            st.session_state.messages.append({"role": "bot", "content": "Is it upper back or lower back?"})
            st.rerun()

        st.session_state.pain_area = area
        # Updated wording here per your request
        follow = (
            "Got it — you mentioned lower back pain. What stage are you in right now (early stages of pain and soreness, or late rehab and strengthening)?"
            if area == "lower back"
            else f"Got it — you mentioned {area} pain. What stage are you in right now (early stages of pain and soreness, or late rehab and strengthening)?"
        )
        st.session_state.messages.append({"role": "bot", "content": follow})
        st.session_state.step = 2
        st.rerun()

# STEP 2 — HISTORY/STAGE → MODE
elif st.session_state.step == 2:

    # If we previously set an explicit chooser, show it now
    if st.session_state.awaiting_stage_choice:
        choice = st.radio(
            "Select your current stage:",
            ["Early stages of pain and soreness (stretch)", "Late rehab and strengthening (strength)"],
            index=None
        )
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("Confirm"):
                if not choice:
                    st.warning("Please pick one option above.")
                    st.stop()
                st.session_state.mode = "stretch" if "stretch" in choice.lower() else "strength"
                st.session_state.awaiting_stage_choice = False
                st.session_state.step = 3  # jump to recommend
                st.rerun()
        with col2:
            if st.button("Back"):
                st.session_state.awaiting_stage_choice = False
                st.rerun()

    user = st.text_area("You:", key="stage_input", placeholder="e.g. early rehab and still sore / late rehab and strengthening")
    if st.button("Send"):
        user = user.strip()
        if not user:
            st.stop()
        st.session_state.messages.append({"role": "user", "content": user})
        st.session_state.history = user

        # First, our fast classifier
        mode = classify_mode(user)

        # If ambiguous, ask Gemini for a one-word choice
        if not mode:
            choice = ask_gemini_free(
                f"You are a physio.\n"
                f"Pain area: {st.session_state.pain_area}.\n"
                f"History: '{user}'.\n"
                f"Choose ONE word only: stretch (if early/sore) or strength (if late rehab/stable).\n"
                f"Answer with only that word."
            ).lower()
            mode = "strength" if "strength" in choice else ("stretch" if "stretch" in choice else "")

        # If still unclear: show explicit chooser instead of defaulting
        if not mode:
            if not st.session_state.asked_clarify_stage:
                st.session_state.asked_clarify_stage = True
                st.session_state.messages.append({"role": "bot", "content": "Quick check: are you still early in pain and soreness (stretch), or in a strengthening phase (strength)?"})
                st.rerun()
            # show chooser on next render
            st.session_state.awaiting_stage_choice = True
            st.rerun()

        st.session_state.mode = mode

        # STEP 3 — RECOMMENDATION
        pain = st.session_state.pain_area
        if pain == "lower back":
            exercise = "Leg Raises" if mode == "stretch" else "Squat"
            reason = "this best matches your current stage and targets the lower back safely."
        else:
            exercise, reason = gemini_pick_exercise(pain, mode)

        st.session_state.exercise_name = exercise
        st.session_state.reasoning = reason

        rec_line = "do a stretch" if mode == "stretch" else "do a strengthening exercise"
        st.session_state.messages.append({
            "role": "bot",
            "content": f"You should {rec_line} because {reason} I recommend the {exercise}. \n\nClick below to get started.",
        })

        st.session_state.step = 3
        st.rerun()

# ==============================
# STEP 3 — REDIRECT + RESTART
# ==============================

elif st.session_state.step == 3:
    st.success(f"Recommended Exercise: {st.session_state.exercise_name}")
    st.write(f"Reason: {st.session_state.reasoning}")

    if st.button("Go to Analyzer"):
        exercise = st.session_state.exercise_name.strip().lower()
        
        # Map exercises to their corresponding pages
        if "squat" in exercise:
            st.switch_page("pages/1_📷️_Live_Stream.py")
        elif "leg" in exercise and "raise" in exercise:
            st.switch_page("pages/3_📷️_Leg_Raises_Live.py")
        elif "stretch" in exercise or "stretching" in exercise:
            # For stretching exercises, default to squats page
            st.switch_page("pages/1_📷️_Live_Stream.py")
        else:
            # Default to squats for any unrecognized exercise
            st.switch_page("pages/1_📷️_Live_Stream.py")

    if st.button("Start Over"):
        for k in list(defaults.keys()):
            st.session_state.pop(k, None)
        st.rerun()

