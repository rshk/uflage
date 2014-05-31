"""
Common functions for uflage
"""

import base64
import hashlib
import hmac
import json


def calculate_signature(key, msg):
    """
    Calculate HMAC signature for ``msg``, using ``key`` and SHA1
    as digest algorithm.

    :param key: The shared key
    :param msg: The message to sign
    :return: The signature, as hexadecimal string
    """
    return hmac.HMAC(key=key, msg=msg, digestmod=hashlib.sha1).hexdigest()


def generate_url(base, key, payload, ext=None):
    """
    Generate URL containing a signed payload.
    """

    payload_str = base64.urlsafe_b64encode(json.dumps(payload))
    if ext is not None:
        payload_str = '{0}.{1}'.format(payload_str, ext)
    signature = calculate_signature(key, payload_str)
    return '{0}/{1}?s={2}'.format(base, payload_str, signature)


def verify_payload(key, payload, signature):
    """
    Verify a signed payload, extracted from a URL
    """

    new_signature = calculate_signature(key, payload)
    if new_signature != signature:
        raise ValueError("Invalid signature")

    # Ignore everything after the dot -- extension is just fancy
    if '.' in payload:
        payload = payload.split('.', 1)[0]

    return json.loads(base64.urlsafe_b64decode(payload))
