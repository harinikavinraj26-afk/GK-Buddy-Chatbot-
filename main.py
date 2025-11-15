import os
import gradio as gr

# -----------------------------
# Quiz data: GK questions, answers, explanations
# -----------------------------
QUESTIONS = [
    {
        "q": "Which is the largest ocean on Earth?",
        "a": "pacific ocean",
        "explain": "The Pacific Ocean is the largest ocean, covering more than 30% of Earth's surface."
    },
    {
        "q": "Who wrote the play 'Romeo and Juliet'?",
        "a": "william shakespeare",
        "explain": "William Shakespeare wrote 'Romeo and Juliet' — one of his most famous tragedies."
    },
    {
        "q": "What is the chemical symbol for water?",
        "a": "h2o",
        "explain": "Water's chemical formula is H₂O, meaning two hydrogen atoms bonded to one oxygen atom."
    },
    {
        "q": "Which planet is known as the Red Planet?",
        "a": "mars",
        "explain": "Mars is called the Red Planet because of iron oxide (rust) on its surface which gives it a reddish appearance."
    },
    {
        "q": "What is the capital city of Japan?",
        "a": "tokyo",
        "explain": "Tokyo is the capital and largest city of Japan."
    },
]

# -----------------------------
# Helper utilities
# -----------------------------
def normalize_text(t):
    if t is None:
        return ""
    return "".join(c for c in t.lower().strip() if c.isalnum() or c.isspace())

def is_answer_correct(user_text, expected):
    # Simple check: normalized expected appears in normalized user_text OR vice versa
    # Also allow short numeric matches and direct equality
    u = normalize_text(user_text)
    e = normalize_text(expected)
    if not u:
        return False
    # direct equality
    if u == e:
        return True
    # contains (accepts longer user inputs that include the answer)
    if e in u:
        return True
    if u in e:
        return True
    # allow answers like "H2O" written as "h2o" or "H 2 O" -> handled by normalize_text
    return False

# -----------------------------
# Chatbot logic
# -----------------------------
def get_reply(user_message, chat_history, state):
    """
    state is a dict with keys:
      mode: "idle" or "quiz"
      q_index: current question index (int) or None
      score: integer
    """
    # Normalize previous history into dict messages (Gradio expects {"role":..., "content":...})
    normalized = []
    if chat_history:
        for item in chat_history:
            if isinstance(item, dict) and "role" in item and "content" in item:
                normalized.append(item)
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                user, bot = item
                normalized.append({"role": "user", "content": str(user)})
                normalized.append({"role": "assistant", "content": str(bot)})
            else:
                normalized.append({"role": "assistant", "content": str(item)})

    # Ensure state keys exist
    mode = state.get("mode", "idle")
    q_index = state.get("q_index", None)
    score = state.get("score", 0)

    user_text = (user_message or "").strip()

    # Commands: start quiz, stop/quit, help
    cmd = user_text.lower().strip()

    if cmd in ("start quiz", "quiz", "start"):
        # Start the quiz
        mode = "quiz"
        q_index = 0
        score = 0
        question_text = QUESTIONS[q_index]["q"]
        # Append messages: user's command and bot asking question
        normalized.append({"role": "user", "content": user_message})
        normalized.append({"role": "assistant", "content": f"Great — starting the GK quiz! Question 1: {question_text}"})
        # save state
        new_state = {"mode": mode, "q_index": q_index, "score": score}
        return normalized, new_state

    if cmd in ("quit", "stop", "exit"):
        # End the quiz / reset
        normalized.append({"role": "user", "content": user_message})
        normalized.append({"role": "assistant", "content": "Quiz stopped. You can type 'start quiz' to try again anytime!"})
        new_state = {"mode": "idle", "q_index": None, "score": 0}
        return normalized, new_state

    if cmd in ("help", "commands"):
        normalized.append({"role": "user", "content": user_message})
        help_text = (
            "I can run a small GK quiz for you. Commands:\n"
            "- 'start quiz' or 'quiz' to begin\n"
            "- Answer questions directly when asked\n"
            "- 'quit' or 'stop' to end the quiz\n"
            "Or just chat normally (say hi)."
        )
        normalized.append({"role": "assistant", "content": help_text})
        new_state = {"mode": mode, "q_index": q_index, "score": score}
        return normalized, new_state

    # If we are in quiz mode, interpret the user's message as an answer
    if mode == "quiz" and q_index is not None and 0 <= q_index < len(QUESTIONS):
        # Append the user's answer into history
        normalized.append({"role": "user", "content": user_message})

        expected = QUESTIONS[q_index]["a"]
        explanation = QUESTIONS[q_index]["explain"]

        if is_answer_correct(user_message, expected):
            # correct
            score += 1
            reply = f"🎉 Correct! {explanation} Good job! 👍"
        else:
            # wrong
            reply = f"❌ That's not correct. The correct answer is: **{QUESTIONS[q_index]['a'].title()}**. {explanation}"

        normalized.append({"role": "assistant", "content": reply})

        # Move to next question or finish
        q_index += 1
        if q_index < len(QUESTIONS):
            next_q_text = QUESTIONS[q_index]["q"]
            normalized.append({"role": "assistant", "content": f"Next question ({q_index+1}/{len(QUESTIONS)}): {next_q_text}"})
            new_state = {"mode": "quiz", "q_index": q_index, "score": score}
        else:
            # quiz finished
            normalized.append({"role": "assistant", "content": f"🏁 Quiz finished! Your score: {score}/{len(QUESTIONS)}."})
            # Appreciation based on score
            if score == len(QUESTIONS):
                normalized.append({"role": "assistant", "content": "Excellent! Perfect score — you're a quiz master! 👏"})
            elif score >= len(QUESTIONS)//2:
                normalized.append({"role": "assistant", "content": "Well done! You did a good job — keep practicing to get perfect."})
            else:
                normalized.append({"role": "assistant", "content": "Nice attempt — try again to improve. You can type 'start quiz' to retry."})
            new_state = {"mode": "idle", "q_index": None, "score": 0}

        return normalized, new_state

    # Not in quiz and not a command -> normal chat responses (small conversational rules)
    normalized.append({"role": "user", "content": user_message})
    low = user_text.lower()
    if any(g in low for g in ["hi", "hello", "hey"]):
        normalized.append({"role": "assistant", "content": "Hello! I can run a GK quiz for you — type 'start quiz' to begin. Or ask me something."})
    elif "thank" in low:
        normalized.append({"role": "assistant", "content": "You're welcome! 😊 If you'd like to try a quiz, type 'start quiz'."})
    else:
        normalized.append({"role": "assistant", "content": "I can help with a small GK quiz. Type 'start quiz' to begin or say 'help' for commands."})

    new_state = {"mode": mode, "q_index": q_index, "score": score}
    return normalized, new_state


# -----------------------------
# Gradio UI helpers and state
# -----------------------------
def respond_and_return_history(user_text, history, state):
    # state is a dict stored in a gr.State object
    if state is None:
        state = {"mode": "idle", "q_index": None, "score": 0}
    new_history, new_state = get_reply(user_text, history, state)
    return new_history, "", new_state


# -----------------------------
# Build Gradio app
# -----------------------------
with gr.Blocks() as demo:
    gr.Markdown("## GK Buddy Chatbot")
    chatbot = gr.Chatbot(type="messages")
    txt = gr.Textbox(placeholder="Type a message and press Enter...")
    clear = gr.Button("Clear Chat")
    state = gr.State({"mode": "idle", "q_index": None, "score": 0})

    txt.submit(respond_and_return_history, [txt, chatbot, state], [chatbot, txt, state])
    # Clear button resets chat and state
    clear.click(lambda: ([], "", {"mode": "idle", "q_index": None, "score": 0}), None, [chatbot, txt, state])

# Launch
port = int(os.environ.get("PORT", 3000))
demo.launch(server_name="0.0.0.0", server_port=port)
