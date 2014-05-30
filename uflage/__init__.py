import base64
import hashlib
import hmac
import json
import os

from flask import Flask, request
from werkzeug.exceptions import NotFound, Unauthorized
import requests


app = Flask(__name__)


VERSION = '0.1'
SECRET_KEY = os.environ.get('UFLAGE_SECRET_KEY') or 'SuperSecret!'
MIME_TYPES = [
    "image/bmp",
    "image/cgm",
    "image/g3fax",
    "image/gif",
    "image/ief",
    "image/jp2",
    "image/jpeg",
    "image/pict",
    "image/png",
    "image/prs.btif",
    "image/svg+xml",
    "image/tiff",
    "image/vnd.adobe.photoshop",
    "image/vnd.djvu",
    "image/vnd.dwg",
    "image/vnd.dxf",
    "image/vnd.fastbidsheet",
    "image/vnd.fpx",
    "image/vnd.fst",
    "image/vnd.fujixerox.edmics-mmr",
    "image/vnd.fujixerox.edmics-rlc",
    "image/vnd.microsoft.icon",
    "image/vnd.ms-modi",
    "image/vnd.net-fpx",
    "image/vnd.wap.wbmp",
    "image/vnd.xiff",
    "image/x-cmu-raster",
    "image/x-cmx",
    "image/x-macpaint",
    "image/x-pcx",
    "image/x-pict",
    "image/x-portable-anymap",
    "image/x-portable-bitmap",
    "image/x-portable-graymap",
    "image/x-portable-pixmap",
    "image/x-quicktime",
    "image/x-rgb",
    "image/x-xbitmap",
    "image/x-xpixmap",
    "image/x-xwindowdump",
]
USERAGENT = "Uflage Proxy v{0}".format(VERSION)


default_security_headers = {
    "X-Frame-Options": "deny",
    "X-XSS-Protection": "1; mode=block",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


def calculate_signature(key, msg):
    return hmac.HMAC(key=key, msg=msg, digestmod=hashlib.sha1).hexdigest()


@app.route('/<payload>')
def serve_resource(payload):
    recv_signature = request.args['s']
    expected_signature = calculate_signature(SECRET_KEY, payload)

    if recv_signature != expected_signature:
        # todo: raise something else to say "bad signature"?
        # Camo does just return 404..
        raise Unauthorized("Bad signature")

    if '.' in payload:
        payload, ext = payload.split('.', 1)
    else:
        ext = None

    request_conf = json.loads(base64.urlsafe_b64decode(payload))

    # Now perform request for the URL in the configuration
    # ------------------------------------------------------------
    rq_url = request_conf['url']
    rq_headers = {
        'Via': USERAGENT,
        'User-agent': USERAGENT,
        'Accept': request.headers.get('accept') or 'image/*',
        'Accept-Encoding': request.headers.get('accept-encoding'),
    }
    for hdr in ("X-Frame-Options", "X-XSS-Protection",
                "X-Content-Type-Options", "Content-Security-Policy"):
        rq_headers[hdr] = default_security_headers[hdr]

    response = requests.get(rq_url, headers=rq_headers)

    # And return the thing as-is to the user
    if not response.ok:
        raise NotFound("Not found")

    # todo: verify the mime type against the extension
    if ext is None:
        pass  # Stop complaining about this being unused!

    # We only return **some** headers from the original response
    resp_headers = {
        'Content-type': response.headers.get('Content-type'),
        'Cache-control': response.headers.get('Cache-control')
        or 'public; max-age=31536000',
        'X-Uflage-Host': 'Unknown',  # For future use..
    }
    for key, val in default_security_headers.iteritems():
        resp_headers[key] = val
    for hdr in ('etag', 'expires', 'last-modified', 'content-length',
                'transfer-encoding', 'content-encoding'):
        if hdr in response.headers:
            resp_headers[hdr] = response.headers[hdr]
    return response.data, 200, resp_headers
