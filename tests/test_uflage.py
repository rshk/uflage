import base64

import pytest

IMGURL_PIMP = 'http://media.ebaumsworld.com/picture/Mincemeat/Pimp.jpg'
IMGURL_SQUIRREL = 'http://dl.dropbox.com/u/602885/github/soldier-squirrel.jpg'
IMGURL_SVG_BOOTSTRAP = 'https://saucelabs.com/browser-matrix/bootstrap.svg'
IMGURL_REALEYES = 'http://27.media.tumblr.com/tumblr_lkp6rdDfRi1qce6mto1_500.jpg'  # noqa
IMGURL_GCHART = ('http://chart.apis.google.com/chart?chs=920x200&chxl=0:%7C'
                 '2010-08-13%7C2010-09-12%7C2010-10-12%7C2010-11-11%7C1:%7C'
                 '0%7C0%7C0%7C0%7C0%7C0&chm=B,EBF5FB,0,0,0&chco=008Cd6&chls'
                 '=3,1,0&chg=8.3,20,1,4&chd=s:AAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
                 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
                 'AAAA&chxt=x,y&cht=lc')


def test_simple_request(testserver):
    """Make sure all the machinery is working"""

    resp = testserver.ts_get('/hello.txt')
    assert resp.ok
    assert resp.status_code == 200
    assert resp.content == 'Hello'
    assert resp.headers['Content-type'] == 'text/plain'


def test_request_image(testserver):
    resp = testserver.get_image('/image.gif')
    expected = base64.decodestring(
        'R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=')
    assert resp.ok
    assert resp.status_code == 200
    assert resp.content == expected
    assert resp.headers['Content-type'] == 'image/gif'


def test_proxy_localhost_test_server(testserver):
    resp = testserver.ts_get('/image.gif')
    assert resp.ok

    resp = testserver.get_image('/image.gif')
    assert resp.ok


def test_proxy_survives_redirect_without_location(testserver):
    resp = testserver.get_image('/redirect_without_location.jpg')
    assert resp.status_code == 404

    resp = testserver.get_image(IMGURL_PIMP)
    assert resp.status_code == 200


def test_follows_https_redirect_for_image_links(testserver):
    resp = testserver.get_image(IMGURL_SQUIRREL)
    assert resp.status_code == 200


def test_doesnt_crash_with_non_url_encoded_url(testserver):
    resp = testserver.proxy_get('/crashme?url=crash&url=me')
    assert resp.status_code == 400


@pytest.mark.xfail(reason='Sending security headers not supported yet')
def test_always_sets_security_headers(testserver):
    for path in ['/', '/status']:
        resp = testserver.proxy_get(path)
        assert resp.status_code == 200
        assert "deny" == resp.headers['x-frame-options']
        assert "default-src 'none'; style-src 'unsafe-inline'" \
            == resp.headers['content-security-policy']
        assert "nosniff" == resp.headers['x-content-type-options']
        assert "max-age=31536000; includeSubDomains" \
            == resp.headers['strict-transport-security']


def test_proxy_valid_image_url(testserver):
    resp = testserver.get_image(IMGURL_PIMP)
    assert resp.status_code == 200


def test_svg_image_with_delimited_content_type_url(testserver):
    resp = testserver.get_image(IMGURL_SVG_BOOTSTRAP)
    assert resp.status_code == 200


def test_png_image_with_delimited_content_type_url(testserver):
    resp = testserver.get_image('http://uploadir.com/u/cm5el1v7')
    assert resp.status_code == 200


def test_proxy_valid_image_url_with_crazy_subdomain(testserver):
    resp = testserver.get_image(IMGURL_REALEYES)
    assert resp.status_code == 200


def test_strict_image_content_type_checking(testserver):
    resp = testserver.get_image("http://calm-shore-1799.herokuapp.com/foo.png")
    assert resp.status_code == 404


def test_proxy_valid_google_chart_url(testserver):
    resp = testserver.get_image(IMGURL_GCHART)
    assert resp.status_code == 200


@pytest.mark.xfail(reason='Chunked transfer is not supported yet')
def test_proxy_valid_chunked_image_file(testserver):
    resp = testserver.get_image(
        'http://www.igvita.com/posts/12/spdyproxy-diagram.png')
    assert resp.status_code == 200
    assert not resp.headers['Content-length']


def test_proxy_https_octocat(testserver):
    resp = testserver.get_image(
        'https://octodex.github.com/images/original.png')
    assert resp.status_code == 200


def test_proxy_https_gravatar(testserver):
    resp = testserver.get_image(
        'https://1.gravatar.com/avatar/a86224d72ce21cd9f5bee6784d4b06c7')
    assert resp.status_code == 200


def test_follows_redirects(testserver):
    resp = testserver.get_image(
        'http://cl.ly/1K0X2Y2F1P0o3z140p0d/boom-headshot.gif')
    assert resp.status_code == 200


def test_follows_redirects_formatted_strangely(testserver):
    resp = testserver.get_image(
        'http://cl.ly/DPcp/Screen%20Shot%202012-01-17%20at%203.42.32%20PM.png')
    assert resp.status_code == 200


def test_follows_redirects_with_path_only_location_headers(testserver):
    resp = testserver.get_image(
        'http://blogs.msdn.com/photos/noahric/images/9948044/425x286.aspx')
    assert resp.status_code == 200


def test_404s_on_request_error(testserver):
    resp = testserver.get_image('/cats.png')
    assert resp.status_code == 404


@pytest.mark.xfail(reason='Needs work')
def test_404s_on_infinidirect(testserver):
    resp = testserver.get_image('http://modeselektor.herokuapp.com/')
    assert resp.status_code == 404


@pytest.mark.skipif(
    True, reason='We need some way to actually send relative URLs to proxy')
def test_404s_on_urls_without_an_http_host(testserver):
    resp = testserver.get_image('/picture/Mincemeat/Pimp.jpg')
    assert resp.status_code == 404


@pytest.mark.skipif(
    True, reason='We need to avoid downloading huge files -- use stream=True')
def test_404s_on_images_greater_than_5_megabytes(testserver):
    imgurl = 'http://apod.nasa.gov/apod/image/0505/larryslookout_spirit_big.jpg'  # noqa
    resp = testserver.get_image(imgurl)
    assert resp.status_code == 404


# def test_404s_on_host_not_found(testserver):
#   assert_raise RestClient::ResourceNotFound do
#     request('http://flabergasted.cx')
#   end
# end

# def test_404s_on_non_image_content_type(testserver):
#   assert_raise RestClient::ResourceNotFound do
#     request('https://github.com/atmos/cinderella/raw/master/bootstrap.sh')
#   end
# end

# def test_404s_on_connect_timeout(testserver):
#   assert_raise RestClient::ResourceNotFound do
#     request('http://10.0.0.1/foo.cgi')
#   end
# end

# def test_404s_on_environmental_excludes(testserver):
#   assert_raise RestClient::ResourceNotFound do
#     request('http://iphone.internal.example.org/foo.cgi')
#   end
# end

# def test_follows_temporary_redirects(testserver):
#   response = request('http://bit.ly/1l9Fztb')
#   assert_equal(200, response.code)
# end

# def test_request_from_self(testserver):
#   assert_raise RestClient::ResourceNotFound do
#     uri = request_uri("http://camo-localhost-test.herokuapp.com")
#     response = request( uri )
#   end
# end

# def test_404s_send_cache_headers(testserver):
#   uri = request_uri("http://example.org/")
#   response = RestClient.get(uri){ |response, request, result| response }
#   assert_equal(404, response.code)
#   assert_equal("0", response.headers[:expires])
#   assert_equal("no-cache, no-store, private, must-revalidate", response.headers[:cache_control]) # noqa
# end
