import gevent
from gevent import monkey
monkey.patch_all()
from flask import Flask, Response
import requests
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
}, service_name='gateway', validate=True, is_async=True)

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
@tracer.trace_inbound_request()
def handle():
    token = 'token'
    headers = {}
    url = 'http://localhost:25003/token/{}/'.format(token)
    with tracer.trace_outbound_request(headers=headers, rpc_name='token'):
        requests.get(url, headers=headers)

    headers = {}
    url = 'http://localhost:25001/assets/{}/'.format(1)
    with tracer.trace_outbound_request(headers=headers, rpc_name='assets'):
        requests.get(url, headers=headers)

    return Response(response='got it!')


app.run(port=28081)
