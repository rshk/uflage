import cgi
import logging
import os

from flask import Flask, request
from werkzeug.exceptions import Unauthorized, BadRequest
import requests

from .lib import verify_payload


app = Flask(__name__)

logger = logging.getLogger(__name__)


VERSION = '0.1'


def get_secret_key():
    return (os.environ.get('UFLAGE_SECRET_KEY')
            or app.config['UFLAGE_SECRET_KEY']
            or 'SuperSecretKey!')

MIME_TYPES = [
    'image/bmp',
    'image/cgm',
    'image/g3fax',
    'image/gif',
    'image/ief',
    'image/jp2',
    'image/jpeg',
    'image/pict',
    'image/png',
    'image/prs.btif',
    'image/svg+xml',
    'image/tiff',
    'image/vnd.adobe.photoshop',
    'image/vnd.djvu',
    'image/vnd.dwg',
    'image/vnd.dxf',
    'image/vnd.fastbidsheet',
    'image/vnd.fpx',
    'image/vnd.fst',
    'image/vnd.fujixerox.edmics-mmr',
    'image/vnd.fujixerox.edmics-rlc',
    'image/vnd.microsoft.icon',
    'image/vnd.ms-modi',
    'image/vnd.net-fpx',
    'image/vnd.wap.wbmp',
    'image/vnd.xiff',
    'image/x-cmu-raster',
    'image/x-cmx',
    'image/x-macpaint',
    'image/x-pcx',
    'image/x-pict',
    'image/x-portable-anymap',
    'image/x-portable-bitmap',
    'image/x-portable-graymap',
    'image/x-portable-pixmap',
    'image/x-quicktime',
    'image/x-rgb',
    'image/x-xbitmap',
    'image/x-xpixmap',
    'image/x-xwindowdump',
]
USER_AGENT = (
    os.environ.get('UFLAGE_USER_AGENT') or
    'Uflage Asset Proxy v{0}'.format(VERSION))
MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 Mb
UFLAGE_HOSTNAME = 'Unknown'  # todo: load from env / hostname

DEFAULT_SECURITY_HEADERS = {
    'X-Frame-Options': 'deny',
    'X-XSS-Protection': '1; mode=block',
    'X-Content-Type-Options': 'nosniff',
    'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'",
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
}


def response_404(reason=None):
    """Simple wrapper to return a 404 response"""
    headers = {
        'Expires': '0',
        'Cache-Control': 'no-cache, no-store, private, must-revalidate',
    }
    if reason is not None:
        headers['X-Failure-reason'] = reason
    headers.update(DEFAULT_SECURITY_HEADERS)
    return 'Not Found', 404, headers


@app.route('/<payload>')
def serve_resource(payload):
    if isinstance(payload, unicode):
        # We need a byte string to b64 decode
        payload = payload.encode('utf-8')

    # Check against loops
    # ------------------------------------------------------------
    if request.headers.get('via') == USER_AGENT:
        logger.error('Requesting from self!')
        return response_404(reason='Loop detected')

    try:
        recv_signature = request.args['s']
    except KeyError:
        raise BadRequest('Signature is required')

    try:
        request_conf = verify_payload(
            get_secret_key(), payload, recv_signature)
    except ValueError:
        logger.error('Invalid signature')
        raise Unauthorized('Invalid signature')
    except:
        raise BadRequest('Invalid request payload')

    # Now perform request for the URL in the configuration
    # ------------------------------------------------------------
    rq_url = request_conf['url']
    rq_headers = {
        'Via': USER_AGENT,
        'User-agent': USER_AGENT,
        'Accept': request.headers.get('accept') or 'image/*',
        'Accept-Encoding': request.headers.get('accept-encoding'),
    }
    for hdr in ('X-Frame-Options', 'X-XSS-Protection',
                'X-Content-Type-Options', 'Content-Security-Policy'):
        rq_headers[hdr] = DEFAULT_SECURITY_HEADERS[hdr]

    # Perform the actual request!
    # ------------------------------------------------------------
    src_resp = requests.get(rq_url, headers=rq_headers)

    # If the request failed in some way, return 404
    # ------------------------------------------------------------
    if src_resp.status_code != 200:
        logger.error('Source returned an error code: {0}'
                     .format(src_resp.status_code))
        return response_404(reason='Source returned an error code: {0}'
                            .format(src_resp.status_code))

    # Check maximum content length, to prevent abuse
    # todo: what if content-length is missing?
    # ------------------------------------------------------------
    content_length = int(src_resp.headers['Content-length'])
    if content_length > MAX_CONTENT_LENGTH:
        logger.error('Maximum content length exceeded')
        return response_404(reason='Maximum content length exceeded')

    # Check content type
    # ------------------------------------------------------------
    content_type = src_resp.headers.get('Content-type', '')
    content_type, content_type_extra = cgi.parse_header(content_type)
    if content_type not in MIME_TYPES:
        logger.error('Disallowed mime type: {0}'.format(content_type))
        raise Unauthorized('Unauthorized mime type.')

    # Prepare headers for the proxied response
    # ------------------------------------------------------------
    new_headers = {
        'Content-type': src_resp.headers['Content-type'],
        'Content-length': src_resp.headers['Content-length'],
        'Cache-control': src_resp.headers.get('Cache-control')
        or 'public, max-age=31536000',
        'X-Uflage-Host': UFLAGE_HOSTNAME,
    }
    new_headers.update(DEFAULT_SECURITY_HEADERS)

    # Pass through some allowed headers
    # ------------------------------------------------------------
    for hdr in ('etag', 'expires', 'last-modified',
                'transfer-encoding', 'content-encoding'):
        if hdr in src_resp.headers:
            new_headers[hdr] = src_resp.headers[hdr]

    return src_resp.content, 200, new_headers
