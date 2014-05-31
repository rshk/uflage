from multiprocessing import Process
import base64
import time
import urllib
import urlparse

from flask import Flask
import pytest
import requests

from uflage.server import app
from uflage.lib import generate_url


SECRET_KEY = "0xB16B00B5BABE"

IMG_GIF = base64.decodestring(
    'R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=')

IMG_JPEG = base64.decodestring("""
/9j/4AAQSkZJRgABAQEASABIAAD//gATQ3JlYXRlZCB3aXRoIEdJTVD/2wBDAAMCAgMCAgMDAwME
AwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/2wBD
AQMEBAUEBQkFBQkUDQsNFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQU
FBQUFBQUFBT/wgARCAABAAEDAREAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACP/EABQBAQAA
AAAAAAAAAAAAAAAAAAD/2gAMAwEAAhADEAAAAVSf/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgB
AQABBQJ//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAA
AAAAAP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAA
AAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9oADAMBAAIAAwAAABCf/8QAFBEBAAAAAAAAAAAAAAAA
AAAAAP/aAAgBAwEBPxB//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPxB//8QAFBABAAAA
AAAAAAAAAAAAAAAAAP/aAAgBAQABPxB//9k= """)

IMG_PNG = base64.decodestring("""
iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVQI12P4//8/AAX+Av7czFnn
AAAAAElFTkSuQmCC """)


class UflageTestWrapper(object):
    def __init__(self):
        self._proxy_proc = None
        self._proxy_port = 8850
        self._ts_proc = None
        self._ts_port = 8860

    app = Flask('uflage.tests')

    @app.route('/hello.txt')
    def view_hello_txt():
        return 'Hello', 200, {'Content-type': 'text/plain'}

    @app.route('/image.gif')
    def view_image_gif():
        return IMG_GIF, 200, {'Content-type': 'image/gif'}

    @app.route('/image.png')
    def view_image_png():
        return IMG_PNG, 200, {'Content-type': 'image/png'}

    @app.route('/image.jpg')
    def view_image_jpeg():
        return IMG_JPEG, 200, {'Content-type': 'image/jpeg'}

    def start(self):
        app.config['UFLAGE_SECRET_KEY'] = SECRET_KEY
        self._proxy_proc = Process(
            target=app.run, kwargs={'port': self._proxy_port,
                                    'debug': True})
        self._proxy_proc.start()

        self._ts_proc = Process(
            target=self.app.run, kwargs={'port': self._ts_port})
        self._ts_proc.start()

        time.sleep(.5)

    def shutdown(self):
        self._proxy_proc.terminate()
        self._ts_proc.terminate()

        # Wait for processes to finish
        self._proxy_proc.join()
        self._ts_proc.join()

    def _get(self, port, path, query):
        url = 'http://localhost:{0}/{1}'.format(
            port, path.lstrip('/'))
        if query:  # Not None nor empty
            url += '?' + urllib.urlencode(query)
        return requests.get(url)

    def proxy_get(self, path, query=None):
        return self._get(self._proxy_port, path, query)

    def ts_get(self, path, query=None):
        return self._get(self._ts_port, path, query)

    def get_image(self, path):
        image_url = urlparse.urljoin(
            'http://localhost:{0}'.format(self._ts_port), path)

        proxy_url = 'http://localhost:{0}'.format(self._proxy_port)
        url = generate_url(proxy_url, SECRET_KEY, {'url': image_url})
        return requests.get(url)


@pytest.fixture
def testserver(request):
    ts = UflageTestWrapper()
    ts.start()
    request.addfinalizer(lambda: ts.shutdown())
    return ts
