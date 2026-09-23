#!/usr/bin/env python
"""Production entry point using Waitress WSGI server"""

import os
import sys
from waitress import serve

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

# FORCE production settings for the WSGI server
os.environ['DJANGO_SETTINGS_MODULE'] = 'point_of_sale.settings_prod'

from point_of_sale.wsgi import application

if __name__ == '__main__':
    print("=" * 60)
    print("Point of Sale System - Production Server")
    print("=" * 60)
    print("Listening on http://0.0.0.0:8085")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    serve(
        application,
        host='0.0.0.0',
        port=8085,
        threads=6,
        connection_limit=100,
    )