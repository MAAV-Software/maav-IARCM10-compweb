from pathlib import Path
import flask
import compweb
import subprocess
import socket
import json
import os
import threading
import time

from compweb.voice import VoiceManager

maav_IARCM10_compweb_dir = Path(__file__).parent.parent.parent
master_drone_destination = "localhost"
master_drone_port = 8000

VOICE_ORBIT_PHRASE = "jarvis start orbit"
VOICE_START_PHRASE = "jarvis start mission"
VOICE_END_PHRASE = "jarvis terminate mission"

VOICE_ORBIT_PHRASE_ALT1 = "jarvis orbit"
VOICE_ORBIT_PHRASE_ALT2 = "start orbit"
VOICE_ORBIT_PHRASE_ALT3 = "start orbit"

VOICE_START_PHRASE_ALT1 = "jarvis start"
VOICE_START_PHRASE_ALT2 = "start mission"
VOICE_START_PHRASE_ALT3 = "start"

VOICE_END_PHRASE_ALT1 = "jarvis start"
VOICE_END_PHRASE_ALT2 = "start mission"
VOICE_END_PHRASE_ALT3 = "start"

speech_message = ""
speech_lock = threading.Lock()

manager = VoiceManager(
    model_path=Path("webapp/models/vosk-model-small-en-us-0.15")
)

session = manager.create_session(threshold=0.5)

def convert_raw_audio_for_vosk():
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i",
        f"{maav_IARCM10_compweb_dir}/audio_data.webm",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-f",
        "s16le",
        "output.raw"
    ])


@compweb.app.route('/')
def show_index():

    print("Reset the audio data file")
    with open("audio_data.webm", "w") as f:
        pass

    context = {}
    instructions = []
    with open(maav_IARCM10_compweb_dir / "compweb" / "static" / "directions.txt", "r") as f:
        for line in f:
            instructions.append(line)
    context["directions"] = instructions
    context["status"] = ""
    return flask.render_template("index.html", **context)

def handle_msg(message_dict, drone_status):
    if message_dict["message_type"] == "ping_status":
        if message_dict["drone_name"] == "drone2":
            drone_status["drone2"] = "Up"
        elif message_dict["drone_name"] == "drone3":
            drone_status["drone3"] = "Up"
        elif message_dict["drone_name"] == "drone4":
            drone_status["drone4"] = "Up"

@compweb.app.route('/ping/', methods=['POST'])
def ping_drones():
    context = {}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # connect to the server
        sock.connect((master_drone_destination, 8000))

        # send a message
        message = json.dumps({"message_type": "ping_drones"})
        sock.sendall(message.encode('utf-8'))

    """Test TCP Socket Server."""
    # Create an INET, STREAMing socket, this is TCP
    # Note: context manager syntax allows for sockets to automatically be
    # closed when an exception is raised or control flow returns.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:

        # Bind the socket to the server
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((master_drone_destination, 8000))
        sock.listen()

        # Socket accept() will block for a maximum of 1 second.  If you
        # omit this, it blocks indefinitely, waiting for a connection.
        sock.settimeout(1)

        while True:
            # Wait for a connection for 1s.  The socket library avoids consuming
            # CPU while waiting for a connection.
            try:
                clientsocket, address = sock.accept()
            except socket.timeout:
                continue
            print("Connection from", address[0])

            # Socket recv() will block for a maximum of 1 second.  If you omit
            # this, it blocks indefinitely, waiting for packets.
            clientsocket.settimeout(1)

            # Receive data, one chunk at a time.  If recv() times out before we
            # can read a chunk, then go back to the top of the loop and try
            # again.  When the client closes the connection, recv() returns
            # empty data, which breaks out of the loop.  We make a simplifying
            # assumption that the client will always cleanly close the
            # connection.
            with clientsocket:
                message_chunks = []
                while True:
                    try:
                        data = clientsocket.recv(4096)
                    except socket.timeout:
                        continue
                    if not data:
                        break
                    message_chunks.append(data)

            # Decode list-of-byte-strings to UTF8 and parse JSON data
            message_bytes = b''.join(message_chunks)
            message_str = message_bytes.decode("utf-8")

            try:
                message_dict = json.loads(message_str)
            except json.JSONDecodeError:
                continue
            drone_status = {}
            drone_status["drone1"] = "Up"
            drone_status["drone2"] = "Down"
            drone_status["drone3"] = "Down"
            drone_status["drone4"] = "Down"
            handle_msg(message_dict, drone_status)
            context["drones"] = drone_status

    return flask.render_template("index.html", **context)


@compweb.app.route('/record/', methods=['POST'])
def record_voice():
    audio_data = flask.request.data

    print("Received:", len(audio_data))

    print(len(audio_data))

    with open("audio_data.webm", "ab") as f:
        f.write(audio_data)

    return {"received": len(audio_data)}

# def set_speech(text):
#     global speech_message

#     with speech_lock:
#         speech_message = text


# @compweb.app.route("/speak")
# def speak():
#     global speech_message

#     with speech_lock:
#         msg = speech_message
#         speech_message = ""   # consume message

#     return flask.jsonify({
#         "message": msg
#     })

@compweb.app.route('/analyze/', methods=['POST'])
def analyze_recording():
    context = {}

    convert_raw_audio_for_vosk()

    with open("output.raw", "rb") as f:
        while True:
            data = f.read(4000)

            if not data:
                break

            session.feed_audio(data)

    orbit_cmds = set([VOICE_ORBIT_PHRASE, VOICE_ORBIT_PHRASE_ALT1, VOICE_ORBIT_PHRASE_ALT2, VOICE_ORBIT_PHRASE_ALT3])
    start_cmds = set([VOICE_START_PHRASE, VOICE_START_PHRASE_ALT1, VOICE_START_PHRASE_ALT2, VOICE_END_PHRASE_ALT3])
    end_cmds = set([VOICE_END_PHRASE, VOICE_END_PHRASE_ALT1, VOICE_END_PHRASE_ALT2, VOICE_END_PHRASE_ALT3])

    finalized_message = session.finalize()
    print(finalized_message)
    if finalized_message["matched_command"] is not None:
        if finalized_message["matched_command"] in start_cmds:
            print("Jarvis will start the mission!")
            
            # Most likely will send a message to the master drone who will then do something on that end outside of the app
            
            # os.system("say 'Jarvis is starting the mission'") # Only works on laptop, need to change to use browser's microphone
            # set_speech("Jarvis is starting the mission")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # connect to the server
                while True:
                    try:
                        sock.connect((master_drone_destination, master_drone_port))
                        break
                    except ConnectionRefusedError:
                        print("Manager not started yet")
                    time.sleep(0.1)

                # send a message
                message = json.dumps({"message_type": "run_drones"})
                sock.sendall((message + "\n").encode("utf-8"))

            status = "Jarvis has started the mission!"

        elif finalized_message["matched_command"] in orbit_cmds:
            print("Jarvis will start orbiting")

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # connect to the server
                while True:
                    try:
                        sock.connect((master_drone_destination, master_drone_port))
                        break
                    except ConnectionRefusedError:
                        print("Manager not started yet")
                    time.sleep(0.1)

                # send a message
                message = json.dumps({"message_type": "orbit_drones"})
                sock.sendall((message + "\n").encode("utf-8"))

            status = "Jarvis will start orbiting!"

        elif finalized_message["matched_command"] in end_cmds:
            print("Jarvis will terminate the mission")

            # os.system("say 'Jarvis is terminating the mission'") # Only works on laptop, need to change to use browser's microphone
            # set_speech("Jarvis is terminating the mission")

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # connect to the server
                while True:
                    try:
                        sock.connect((master_drone_destination, master_drone_port))
                        break
                    except ConnectionRefusedError:
                        print("Manager not started yet")
                    time.sleep(0.1)

                # send a message
                message = json.dumps({"message_type": "terminate_drones"})
                sock.sendall((message + "\n").encode("utf-8"))

            status = "Jarvis has terminated the mission!"

        else:
            print("Unknown matched command")

        context["status"] = status

    with open("audio_data.webm", "w") as f:
        pass

    instructions = []
    with open(maav_IARCM10_compweb_dir / "compweb" / "static" / "directions.txt", "r") as f:
        for line in f:
            instructions.append(line)
    context["directions"] = instructions
    
    return flask.render_template("index.html", **context)
