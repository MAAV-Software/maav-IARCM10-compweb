import flask
from flask_cors import CORS

app = flask.Flask(__name__)
app.config.from_object('compweb.config')
CORS(app)

import compweb.views
import compweb.model

print(app.url_map)