# Friday

Your voice-first personal AI assistant. Talk to it, and it remembers things about you, manages your
tasks and reminders, tracks your bills, sets up payments for you to approve, and searches the web.
Claude does the thinking.

> **Friday never moves money on its own.** It builds a ready-to-go UPI / payment link,
> and you approve it with your own PIN. This is deliberate. See "Why it doesn't pay for you" below.

## What you can say

- "Remember I'm allergic to peanuts." / "What do you know about me?"
- "Remind me to call Mom tomorrow at 6 pm." / "What's on my list?" / "Mark call Mom done."
- "Track my electricity bill, about 1450 rupees, due on the 10th, UPI bses@okhdfc."
- "What bills are due?" → "Pay the electricity bill." (a **Pay** button opens GPay/PhonePe, already filled in)
- "I paid it." (Friday marks it paid for this month)
- "What's the weather in Delhi?" / "Latest news on ISRO?" (live web search)
- "Stop" or "bye" ends hands-free mode.

When a bill is due within 3 days, or a reminder is due within an hour, Friday tells you out loud while the page is open.

## Setup (one time, about 10 minutes)

**1. Get an API key (this is Friday's brain).**
Go to https://console.anthropic.com, sign up, add a few dollars of credit, then open **API Keys → Create Key**.
Copy the key. It starts with `sk-ant-`. Treat it like a password.

**2. Install Python 3.10 or newer** (skip this if you have it): https://www.python.org/downloads/
On Windows, **tick "Add python.exe to PATH"** in the installer.

**3. Download Friday.** On GitHub, switch to the `friday` branch, then **Code → Download ZIP**, and unzip it.
Open the `friday` folder.

**4. Start it.**
- **Windows:** double-click `start.bat`
- **Mac / Linux:** open Terminal in the folder and run `./start.sh`

The first run installs everything and opens a `.env` file. Paste your key after `ANTHROPIC_API_KEY=`,
save the file, and run the start script again.

**5. Talk.** Your browser opens http://localhost:8000. Enter the **passcode** printed in the terminal
window, allow the microphone, tap the glowing orb and speak. Tick **Hands-free** to keep chatting
without tapping.

Use **Chrome or Edge** on a computer. Firefox can't do voice input; you can still type.

## On your phone

Your computer runs Friday, and your phone connects to it. Browsers only allow the microphone on secure
(https) pages, so you need a free secure tunnel:

1. Install cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
2. With Friday running, open a second terminal and run:
   `cloudflared tunnel --url http://localhost:8000`
3. It prints a `https://something.trycloudflare.com` link. Open it on your phone in Chrome (Android)
   or Safari (iPhone) and enter your passcode.
4. Add it to your home screen (**Share → Add to Home Screen**, or Chrome **⋮ → Add to Home screen**).
   It then opens like an app.

The link changes every time you restart the tunnel. Anyone who has the link still needs your passcode.

## Settings (`.env` file)

| Setting | What it does |
|---|---|
| `ANTHROPIC_API_KEY` | Required. Friday's brain. |
| `FRIDAY_USER_NAME` | What Friday calls you. Default: Boss |
| `FRIDAY_PASSCODE` | Your own passcode. If you leave it out, one is generated and saved in `data/passcode.txt` |
| `FRIDAY_EFFORT` | `low` (fastest, default), `medium`, `high` (smarter but slower) |

Your memories, tasks and bills are stored only on your computer, in `data/friday.json`.

## Why it doesn't pay for you

You asked for autopay. Here's why that's a bad idea:

- **No legal API exists for this.** Indian banks and UPI apps don't let a personal app debit your account
  without your PIN. An AI that types your PIN or OTP for you is a security hole, not a feature.
- **AI makes mistakes.** If it mishears "fifteen" as "fifty" with your PIN on file, the money is gone.
  A one-tap approval costs you 3 seconds.
- **The real fix already exists.** For fixed bills (rent, EMI, subscriptions, phone), set up
  **UPI AutoPay or a bank standing instruction once**. Then Friday's job is to remind you and check the
  bills got paid. That's actual automation, and the bank stays legally on the hook for it.

## What's not here yet (and why)

| Missing | Why |
|---|---|
| "Hey Friday" wake word | A browser can't listen all the time. Needs a desktop app. Next version. |
| Gmail / Calendar | Needs Google sign-in setup (OAuth). Next version, after you've used this one for a week. |
| Smart home | Needs your devices' details (e.g. Home Assistant). Tell me what you have. |
| Runs while the page is closed | Reminders only speak while Friday's page is open. |

## Cost

Each question costs roughly ₹0.5–3 on Claude Opus 5.5 at the default `low` effort. Web searches cost more.
Set a monthly spending limit in the Anthropic console.
