import logging
from datetime import datetime

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
}, service_name='metadata', validate=True)

app = Flask(__name__)


@app.route('/metadata/assets/<string:asset_id>/')
@tracer.trace_inbound_request()
def get_asset_metadata(asset_id):
    return jsonify({
        'title': 'Asset {}'.format(asset_id),
        'status': 'CLOSED',
        'date_created': datetime.now().isoformat(),
    })


if __name__ == '__main__':
    app.run(port=25005)
