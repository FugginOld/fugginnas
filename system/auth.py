import os
from flask import request, jsonify


def register_auth(app):
    @app.before_request
    def enforce_localhost():
        if request.remote_addr not in ('127.0.0.1', '::1'):
            return jsonify({'error': 'forbidden'}), 403

    @app.before_request
    def check_password():
        password = os.environ.get('FUGGINNAS_PASSWORD', '')
        if not password:
            return
        if not request.path.startswith('/api/'):
            return
        auth = request.headers.get('Authorization', '')
        if auth != f'Bearer {password}':
            return jsonify({'error': 'unauthorized'}), 401
