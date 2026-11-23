"""Say something, then say "post that", and it goes to X.

Live transcription: AssemblyAI-STT-3.7-Realtime through the AssemblyAI Python SDK.
Posting: POST https://api.x.com/2/tweets with OAuth 1.0a user context.
"""

import argparse
import os
import re
import threading

import pyaudio
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session
from assemblyai.streaming.v3 import (
    BeginEvent,
    RealTimeError,
    RealTimeEvents,
    RealTimeParameters,
    RealTimeTranscriber,
    RealTimeTranscriberOptions,
    TerminationEvent,
    TurnEvent,
)

load_dotenv()

SAMPLE_RATE = 16000
FRAMES_PER_BUFFER = 800  # 50 ms of 16-bit mono PCM at 16 kHz
X_POST_URL = "https://api.x.com/2/tweets"
MAX_POST_CHARS = 280  # X's limit for accounts without X Premium

# "post that" / "tweet that" at the end of a turn, with optional trailing punctuation.
COMMAND = re.compile(r"^(?P<before>.*?)[\s,]*\b(?:post|tweet) that[\s.!?]*$", re.IGNORECASE)

state = {"previous_turn": "", "last_posted": ""}
lock = threading.Lock()

# ---------- X ----------

def make_x_session() -> OAuth1Session:
    return OAuth1Session(
        client_key=os.environ["X_API_KEY"],
        client_secret=os.environ["X_API_KEY_SECRET"],
        resource_owner_key=os.environ["X_ACCESS_TOKEN"],
        resource_owner_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def post_to_x(session, text: str, dry_run: bool) -> None:
    text = text.strip()
    if len(text) > MAX_POST_CHARS:
        text = text[: MAX_POST_CHARS - 1] + "…"

    if dry_run:
        print(f"[dry run] would post: {text!r}")
        return

    response = session.post(X_POST_URL, json={"text": text})
    if response.status_code == 201:
        post_id = response.json()["data"]["id"]
        print(f"Posted to X (id {post_id}): {text}")
    else:
        print(f"X returned {response.status_code}: {response.text}")

# ---------- Commands ----------

def handle_final_turn(text: str, session, dry_run: bool) -> None:
    """Post the earlier part of this turn, or the previous turn, when it ends in 'post that'."""
    match = COMMAND.match(text)
    if not match:
        with lock:
            state["previous_turn"] = text
        return

    with lock:
        before = match.group("before").strip()
        # "Okay, post that" -> post the previous turn; a real sentence before the command -> post it.
        payload = before if len(before.split()) >= 3 else state["previous_turn"]
        if not payload:
            print("Heard the command, but there's nothing to post yet.")
            return
        if payload == state["last_posted"]:
            print("Skipping a duplicate post.")
            return
        state["last_posted"] = payload
        state["previous_turn"] = ""

    post_to_x(session, payload, dry_run)

# ---------- Microphone ----------

def microphone_chunks(stop: threading.Event):
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=FRAMES_PER_BUFFER,
    )
    try:
        while not stop.is_set():
            yield stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()

# ---------- Main ----------

def main() -> None:
    parser = argparse.ArgumentParser(description="Post to X by voice.")
    parser.add_argument("--dry-run", action="store_true", help="print posts instead of sending them")
    args = parser.parse_args()

    session = None if args.dry_run else make_x_session()

    def on_begin(client: RealTimeTranscriber, event: BeginEvent):
        print(f"Session {event.id} started. Talk, then say 'post that'. Ctrl+C to stop.")

    def on_turn(client: RealTimeTranscriber, event: TurnEvent):
        if not event.transcript:
            return
        if event.end_of_turn:
            print(f"\r{event.transcript}")
            handle_final_turn(event.transcript, session, args.dry_run)
        else:
            print(f"\r{event.transcript}", end="", flush=True)

    def on_terminated(client: RealTimeTranscriber, event: TerminationEvent):
        print(f"\nSession ended after {event.audio_duration_seconds}s of audio.")

    def on_error(client: RealTimeTranscriber, error: RealTimeError):
        print(f"\nStreaming error: {error}")

    client = RealTimeTranscriber(
        RealTimeTranscriberOptions(),
        api_key=os.environ["ASSEMBLYAI_API_KEY"],
    )
    client.on(RealTimeEvents.Begin, on_begin)
    client.on(RealTimeEvents.Turn, on_turn)
    client.on(RealTimeEvents.Termination, on_terminated)
    client.on(RealTimeEvents.Error, on_error)

    client.connect(
        RealTimeParameters(
            speech_model="assemblyai-stt-3-7-realtime",
            sample_rate=SAMPLE_RATE,
        )
    )

    stop = threading.Event()
    try:
        client.stream(microphone_chunks(stop))
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        client.disconnect(terminate=True)


if __name__ == "__main__":
    main()
