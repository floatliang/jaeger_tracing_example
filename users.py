import logging

from flask import Flask, request
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
}, service_name='user', validate=True)

app = Flask(__name__)


@app.route('/users/<string:user_id>/', methods=['GET', 'POST'])
@tracer.trace_inbound_request()
def get_user(user_id):
    if request.method == 'GET':
        return jsonify({'id': user_id, 'name': 'User {}'.format(user_id)})
    elif request.method == 'POST':
        return request.POST


if __name__ == '__main__':
    app.run(port=25004)
