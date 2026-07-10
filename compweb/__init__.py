import flask

app = flask.Flask(__name__)
app.config.from_object('compweb.config')

import compweb.views
import compweb.model

print(app.url_map)