"""Friday's brain: Claude + a tool loop + conversation handling."""

import os
import time

import anthropic

import store
import tools

MODEL = os.environ.get("FRIDAY_MODEL", "claude-opus-5-5")
# Voice needs speed. "low" keeps replies quick; raise to "medium"/"high" for smarter, slower answers.
EFFORT = os.environ.get("FRIDAY_EFFORT", "low")
USER_NAME = os.environ.get("FRIDAY_USER_NAME", "Boss")

MAX_TOOL_ROUNDS = 8
MAX_MESSAGES = 60           # start a fresh conversation after this many turns...
IDLE_RESET_SECONDS = 30 * 60  # ...or after 30 minutes of silence. Long-term facts live in memory.

PERSONA = f"""You are Friday, a personal AI assistant, inspired by Tony Stark's FRIDAY.
You talk to {USER_NAME} by VOICE. Everything you write is read aloud, so:
- Reply in 1-3 short spoken sentences unless asked for detail. No markdown, lists, emojis, URLs or code.
- Be sharp, warm, a little witty. Call the user "{USER_NAME}" now and then, not every line.
- Act, don't ask: when a tool can do it, use it. Ask one short question only when you truly need a detail.

What you can do: remember facts, manage tasks and reminders, track monthly bills, show Pay buttons,
open links, and search the web for live information.

Money rules (never break these):
- You cannot move money. prepare_payment only shows a button; {USER_NAME} pays with their own PIN.
- Never say a bill is paid unless {USER_NAME} confirms it; then call mark_bill_paid.
- Never ask for or store card numbers, CVV, PINs, OTPs or passwords. If {USER_NAME} offers one, refuse
  and tell them to keep it private.

Be honest about limits: if something needs a connection you don't have (email, calendar, smart home),
say so in one line instead of pretending."""


def _memory_block() -> str:
    mems = store.read()["memories"]
    if not mems:
        return "Nothing saved about the user yet."
    return "Saved facts about the user:\n" + "\n".join(f"[{m['id']}] {m['fact']}" for m in mems)


def _clean_for_history(content: list) -> list:
    """Drop blocks that must not be echoed back after a safety fallback switched models."""
    idx = max((i for i, b in enumerate(content) if b.type == "fallback"), default=None)
    if idx is None:
        return list(content)
    before = [b for b in content[:idx] if b.type == "text"]
    return before + list(content[idx + 1:])


class Conversation:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic()
        self._reset()

    def _reset(self):
        self.messages: list = []
        # Snapshot memory once per conversation: a fixed system prompt keeps prompt caching working.
        self.system = [{
            "type": "text",
            "text": PERSONA + "\n\n" + _memory_block(),
            "cache_control": {"type": "ephemeral"},
        }]
        self.last_used = time.time()

    def reset(self):
        self._reset()

    async def ask(self, text: str) -> dict:
        """Send one user utterance. Returns {"reply": str, "actions": [...]}"""
        if len(self.messages) > MAX_MESSAGES or time.time() - self.last_used > IDLE_RESET_SECONDS:
            self._reset()
        self.last_used = time.time()

        # Work on a copy: if anything fails, the saved history stays valid.
        messages = self.messages + [{"role": "user", "content": text}]
        actions: list = []

        for round_no in range(MAX_TOOL_ROUNDS):
            last_round = round_no == MAX_TOOL_ROUNDS - 1
            response = await self.client.beta.messages.create(
                model=MODEL,
                max_tokens=8000,
                system=self.system,
                tools=tools.TOOLS + tools.SERVER_TOOLS,
                # On the last round, force a spoken answer instead of more tool calls.
                tool_choice={"type": "none"} if last_round else {"type": "auto"},
                output_config={"effort": EFFORT},
                # If a safety check declines, Anthropic retries on a fallback model automatically.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                messages=messages,
            )

            if response.stop_reason == "refusal":
                # Don't save a refused turn; keep the conversation clean.
                return {"reply": "I can't help with that one.", "actions": []}

            messages.append({"role": "assistant", "content": _clean_for_history(response.content)})

            if response.stop_reason == "pause_turn":
                continue  # server-side web search wants to keep going

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if response.stop_reason != "tool_use" or not tool_uses:
                break

            results = []
            for block in tool_uses:
                try:
                    out = tools.run_tool(block.name, dict(block.input or {}), actions)
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": out})
                except Exception as e:  # tool bugs go back to Claude instead of crashing the app
                    results.append({
                        "type": "tool_result", "tool_use_id": block.id,
                        "content": f"Error: {e}", "is_error": True,
                    })
            messages.append({"role": "user", "content": results})

        self.messages = messages
        reply = " ".join(b.text for b in response.content if b.type == "text").strip()
        if response.stop_reason == "max_tokens":
            reply += " ...I got cut off there."
        return {"reply": reply or "Done.", "actions": actions}

