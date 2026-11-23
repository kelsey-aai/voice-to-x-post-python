# Post to X with your voice (Python)

Companion code for the AssemblyAI blog tutorial [Auto-tweet your words with real-time speech recognition in Python](https://www.assemblyai.com/blog/auto-tweet-your-words-using-speech-recognition-in-python).

Talk into your microphone. Live text appears as you speak. When you say **"post that"** (or "tweet that"), the app posts what you just said to X.

- Live transcription: [AssemblyAI-STT-3.7-Realtime](https://www.assemblyai.com/docs/streaming/select-the-speech-model) (`assemblyai-stt-3-7-realtime`) through the AssemblyAI Python SDK.
- Posting: `POST https://api.x.com/2/tweets` with OAuth 1.0a user context, per [X's Create Post reference](https://docs.x.com/x-api/posts/create-post).

## How the command works

| You say | What gets posted |
|---|---|
| "I think tabs beat spaces. Post that." (one turn) | "I think tabs beat spaces." |
| "Coffee is a vegetable." then, as a new turn, "Post that." | "Coffee is a vegetable." |
| "Okay, post that." after a turn | The previous turn (a filler word before the command doesn't count as the post) |

The same text is never posted twice in a row. Posts over 280 characters are trimmed, since that's X's limit for accounts without X Premium.

## Setup

Requires Python 3.9+ and a microphone. PyAudio needs PortAudio (`brew install portaudio` on macOS, `sudo apt install portaudio19-dev` on Debian/Ubuntu).

```bash
git clone https://github.com/kelsey-aai/voice-to-x-post-python.git
cd voice-to-x-post-python
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
```

**X credentials.** In the [X Developer Console](https://console.x.com), create an app, set its permissions to **Read and write**, and generate the Access Token and Secret for your account. If you change permissions after generating tokens, generate new ones. The X API is pay-per-use; check [X's pricing page](https://docs.x.com/x-api/getting-started/pricing) before you post a lot.

## Run

```bash
# Try it without posting anything
python voice_post.py --dry-run

# Post for real
python voice_post.py
```

Press Ctrl+C to stop. The app sends a terminate message so the last turn is finalized before the session closes.
