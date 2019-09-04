from flask import Flask
from flask import jsonify
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
}, service_name='asset', validate=True)

app = Flask(__name__)


@app.route('/assets/<int:asset_id>/')
@tracer.trace_inbound_request()
def hello(asset_id):
    headers = {}
    with tracer.trace_outbound_request(headers=headers, rpc_name='metadata'):
        response = requests.get('http://localhost:25005/metadata/assets/{}/'.format(asset_id), headers=headers)
    return jsonify({
        'id': asset_id,
        'name': 'Asset {}'.format(asset_id),
        'metadata': response.json()
    })


if __name__ == '__main__':
    app.run(port=25001)
