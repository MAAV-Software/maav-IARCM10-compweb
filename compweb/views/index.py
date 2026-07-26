
import sounddevice as sd
from pathlib import Path
import flask
import compweb
import time
import threading
import json

from compweb.voice import VoiceManager

print("compweb.views imported")

stop_event = threading.Event()

manager = VoiceManager(
    model_path=Path("webapp/models/vosk-model-small-en-us-0.15")
)

session = manager.create_session(threshold=0.5)

@compweb.app.route('/')
def show_index():
    context = {}
    return flask.render_template("index.html", **context)

@compweb.app.route('/api/record', methods=['POST'])
def api_record():
    return flask.jsonify({"status": "ok"})

@compweb.app.route('/record/', methods=['POST'])
def record_voice():
    stop_event.clear()
    thread1 = threading.Thread(target=record_voice)

    thread1.start()
    context = {}
    return flask.render_template("index.html", **context)

@compweb.app.route('/stop_record/', methods=['POST'])
def stop_recording_voice():
    stop_event.set()
    context = {}
    finalized_message = session.finalize()
    print(finalized_message)
    if finalized_message["matched_command"] is not None:
        if finalized_message["matched_command"] == "jarvis start mission":
            print("Jarvis will start the mission!")
            
            # Most likely will send a message to the master drone who will then do something on that end outside of the app
            pass
        elif finalized_message["matched_command"] == "jarvis terminate mission":
            print("Jarvis will terminate the mission")

            # Most likely will send a message to the master drone who will then do something on that end outside of the app
            pass
        else:
            print("Unknown matched command")
    return flask.render_template("index.html", **context)
    

def record_voice():

    sample_rate = manager.sample_rate_hz
    with sd.RawInputStream(
        samplerate=sample_rate,
        blocksize=8000,
        dtype="int16",
        channels=1,
    ) as stream:

        while not stop_event.is_set():
            data, overflowed = stream.read(4000)

            event = session.feed_audio(bytes(data))

            if event:
                print(event)
            
            time.sleep(0.1)
        
        print("Ended loop")