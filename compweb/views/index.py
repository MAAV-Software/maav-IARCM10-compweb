from pathlib import Path
import flask
import compweb
import subprocess
import socket
import json

from compweb.voice import VoiceManager

maav_IARCM10_compweb_dir = Path(__file__).parent.parent.parent
master_drone_destination = "192.168.4.1"

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

@compweb.app.route('/analyze/', methods=['POST'])
def analyze_recording():
    context = {}

    print("Here")
    convert_raw_audio_for_vosk()

    with open("output.raw", "rb") as f:
        while True:
            data = f.read(4000)

            if not data:
                break

            session.feed_audio(data)

    finalized_message = session.finalize()
    print(finalized_message)
    if finalized_message["matched_command"] is not None:
        if finalized_message["matched_command"] == "jarvis start mission":
            print("Jarvis will start the mission!")
            
            # Most likely will send a message to the master drone who will then do something on that end outside of the app
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # connect to the server
                sock.connect((master_drone_destination, 8000))

                # send a message
                message = json.dumps({"message_type": "run_drones"})
                sock.sendall(message.encode('utf-8'))
        elif finalized_message["matched_command"] == "jarvis terminate mission":
            print("Jarvis will terminate the mission")

            # Most likely will send a message to the master drone who will then do something on that end outside of the app
            # with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            #     # connect to the server
            #     sock.connect((master_drone_destination, 8000))

            #     # send a message
            #     message = json.dumps({"message_type": "terminate_drones"})
            #     sock.sendall(message.encode('utf-8'))
        else:
            print("Unknown matched command")

    with open("audio_data.webm", "w") as f:
        pass
    return flask.render_template("index.html", **context)
