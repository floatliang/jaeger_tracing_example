import logging

import requests
from flask import Flask
from flask import jsonify

from flask_tracer import FlaskTracer

tracer = FlaskTracer(config={
    'sampler': {
        'type': 'const',
        'param': 1,
    },
    'local_agent': {
        'reporting_host': '',
        'reporting_port': '',
        'sampling_port': ''
    },
    'logging': True
}, service_name='auth', validate=True)

app = Flask(__name__)


@app.route('/token/<string:token>/')
@tracer.trace_inbound_request()
def hello(token):
    headers = {}
    url = 'http://localhost:25004/users/1/'
    with tracer.trace_outbound_request(headers=headers, rpc_name='users'):
        response = requests.get(url, headers=headers)

    result = jsonify({'token': token, 'access': 'granted', 'user': response.json()})

    return result


if __name__ == '__main__':
    app.run(port=25003)
