import json
import hashlib
import pathlib
import socket
import flask
import compweb

print("compweb.views imported")

@compweb.app.route('/')
def show_index():
    context = {}
    return flask.render_template("index.html", **context)

@compweb.app.route('/send/', methods=['POST'])
def send_message():
    target = flask.request.args.get("target", "/")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:

        # connect to the server
        sock.connect(("192.168.1.35", 8000))

        # send a message
        message = json.dumps({"message_type": "run_drones"})
        sock.sendall(message.encode('utf-8'))
    return flask.redirect(target)
