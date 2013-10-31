import sys
import os
import shutil

from StringIO import StringIO
from urllib import urlencode
from pytest import raises

from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.model.bag import Bag
from tiddlyweb.model.policy import Policy
from tiddlyweb.store import NoTiddlerError, NoBagError
from tiddlyweb.config import config as CONFIG
from tiddlyweb.manage import handle
from tiddlyweb.web.util import make_cookie

from . import make_instance, req as _req, StreamCapture


def setup_module(module):
    module.TMPDIR, module.STORE, module.ADMIN_COOKIE = make_instance()

    bag = Bag('alpha')
    bag.policy = Policy(read=['admin'], write=['admin'], create=['admin'],
            delete=['admin'], manage=['admin'])
    STORE.put(bag)

    bag = Bag('bravo')
    STORE.put(bag)

    bag = Bag('charlie')
    bag.policy = Policy(read=['nobody'], write=['nobody'], create=['nobody'],
            delete=['nobody'], manage=['nobody'])
    STORE.put(bag)

    tiddler = Tiddler('index', 'bravo')
    tiddler.text = 'lorem ipsum\ndolor *sit* amet'
    tiddler.type = 'text/x-markdown'
    STORE.put(tiddler)


def teardown_module(module):
    shutil.rmtree(TMPDIR)


def test_assetcopy(): # XXX: does not belong here
    target_dir = os.path.join(TMPDIR, 'static_assets')
    # capture STDERR to avoid confusion
    with StreamCapture('stderr') as stream:
        with raises(SystemExit): # no directory provided
            handle(['', 'assetcopy'])

        handle(['', 'assetcopy', target_dir])

        entries = os.listdir(target_dir)
        assert 'favicon.ico' in entries

        with raises(SystemExit): # directory already exists
            handle(['', 'assetcopy', target_dir])


def test_integration(): # XXX: does not belong here
    bag = Bag('snippets')
    STORE.put(bag)

    tiddler = Tiddler('index', 'snippets')
    tiddler.text = 'lipsum'
    tiddler.tags = ['foo', 'bar']
    STORE.put(tiddler)

    response, content = _req('GET', '/tags/foo')
    assert response.status == 200

    response, content = _req('GET', '/tags/bar')
    assert response.status == 200

    with StreamCapture('stdout') as stream:
        handle(['', 'tags'])

        stream.seek(0)
        assert stream.read() == "foo\nbar\n"


def test_root():
    response, content = _req('GET', '/')
    assert response.status == 200
    assert response['content-type'] == 'text/html; charset=UTF-8'

    assert 'Log in' in content
    assert 'Register' in content
    uri = 'https://github.com/FND/tiddlywebplugins.bfw'
    assert '<a href="%s">BFW</a>' % uri in content

    frontpage = Tiddler('index', 'meta')
    STORE.delete(frontpage) # XXX: side-effecty
    response, content = _req('GET', '/')
    assert response.status == 200
    assert '<a href="%s">BFW</a>' % uri not in content

    response, content = _req('GET', '/', headers={ 'Cookie': ADMIN_COOKIE })
    assert response.status == 302
    assert response['location'] == '/~'


def test_user_home():
    response, content = _req('GET', '/~')
    assert response.status == 401

    response, content = _req('GET', '/~', headers={ 'Cookie': ADMIN_COOKIE })
    assert response.status == 200
    assert '<a href="/meta">meta</a>' in content
    assert '<a href="/admin">admin</a>' in content
    assert '<a href="/alpha">alpha</a>' in content
    assert '<a href="/bravo">bravo</a>' in content
    assert not 'charlie' in content
    assert '<option value="meta">' not in content
    assert '<option value="admin">' in content
    assert '<option value="alpha">' in content
    assert '<option value="bravo">' in content

    response, content = _req('GET', '/~', headers={ 'Cookie': ADMIN_COOKIE })
    assert response.status == 200
    assert "admin's personal wiki" in content

    index = Tiddler('index', 'admin')
    STORE.delete(index)
    response, content = _req('GET', '/~', headers={ 'Cookie': ADMIN_COOKIE })
    assert response.status == 200

    response, content = _req('GET', '/', headers={ 'Cookie': ADMIN_COOKIE })
    assert response.status == 302
    assert response['location'] == '/~'


def test_wiki_page():
    response, content = _req('GET', '/alpha/index')
    assert response.status == 302
    assert '/challenge?tiddlyweb_redirect=%2Falpha%2Findex' in response['location']
    assert response['location'].endswith('/challenge?tiddlyweb_redirect=%s' %
            '%2Falpha%2Findex')

    response, content = _req('GET', '/bravo/index')
    assert response.status == 200
    assert '<p>lorem ipsum\ndolor <em>sit</em> amet</p>' in content
    assert '<a href="/editor?page=bravo%2Findex">edit</a>' in content

    response, content = _req('GET', '/bravo/HelloWorld')
    assert response.status == 302
    assert response['location'] == '/editor?page=bravo%2FHelloWorld'


def test_page_editor():
    response, content = _req('GET', '/editor?page=alpha%2FHelloWorld')
    assert response.status == 302
    assert response['location'].endswith('/challenge?tiddlyweb_redirect=%s' %
            '%2Feditor%3Fpage%3Dalpha%252FHelloWorld')

    response, content = _req('GET', '/editor?page=bravo%2FHelloWorld')
    assert response.status == 200
    assert '<form ' in content
    assert 'action="/pages"' in content
    assert 'method="post"' in content
    assert '<title>bravo/HelloWorld</title>' in content
    assert '<h1>HelloWorld</h1>' in content
    assert '<input type="hidden" name="wiki" value="bravo">' in content
    assert '<input type="hidden" name="title" value="HelloWorld">' in content
    assert '<textarea name="text" data-widearea="enable"></textarea>' in content
    assert '"HelloWorld" does not exist yet in wiki "bravo"' in content

    response, content = _req('GET', '/editor?page=bravo%2Findex')
    assert response.status == 200
    assert '<textarea name="text" data-widearea="enable">lorem ipsum\ndolor *sit* amet</textarea>' in content
    assert not 'does not exist yet' in content


def test_user_registration():
    headers = { 'Content-Type': 'application/x-www-form-urlencoded' }
    data = {
        'username': 'fnd',
        'password': 'foo',
        'password_confirmation': 'foo'
    }

    assert not _bag_exists('fnd')

    response, content = _req('POST', '/register', urlencode(data),
            headers=headers)
    assert response.status == 303
    assert 'tiddlyweb_user="fnd:' in response['set-cookie']
    bag = _bag_exists('fnd')
    assert bag
    assert bag.policy.read == ['fnd']

    bag = Bag('sandbox')
    STORE.put(bag)
    _data = {}
    _data.update(data)
    _data['username'] = 'sandbox'
    response, content = _req('POST', '/register', urlencode(_data),
            headers=headers)
    assert response.status == 409

    response, content = _req('POST', '/register', urlencode(data),
            headers=headers)
    assert response.status == 409 # already exists

    data['username'] = 'wikis'
    response, content = _req('POST', '/register', urlencode(data),
            headers=headers)
    assert response.status == 409 # blacklisted

    # ensure personal index page is created automatically
    data = {
        'username': 'dummy',
        'password': 'foo',
        'password_confirmation': 'foo'
    }
    response, content = _req('POST', '/register', urlencode(data),
            headers={ 'Content-Type': 'application/x-www-form-urlencoded' })
    cookie = make_cookie('tiddlyweb_user', 'dummy', mac_key=CONFIG['secret'])
    response, content = _req('GET', '/~', headers={ 'Cookie': cookie })
    assert response.status == 200
    assert "dummy's personal wiki" in content


def test_login():
    headers = { 'Content-Type': 'application/x-www-form-urlencoded' }
    data = {
        'user': 'fnd',
        'password': 'foo'
    }
    response, content = _req('POST', '/challenge/cookie_form', urlencode(data),
            headers=headers)

    assert response.status == 303
    assert 'tiddlyweb_user="fnd:' in response['set-cookie']

    response, content = _req('POST', '/logout')

    assert response.status == 303
    assert response['set-cookie'] == 'tiddlyweb_user=; Max-Age=0; Path=/'
    assert response['location'] == 'http://example.org:8001/'


def test_wiki_creation():
    assert not _bag_exists('foo')

    default_headers = { 'Content-Type': 'application/x-www-form-urlencoded' }
    data = {
        'wiki': 'foo',
        'private': '1'
    }

    response, content = _req('POST', '/wikis')
    assert response.status == 415

    response, content = _req('POST', '/wikis', urlencode(data),
            headers=default_headers)
    assert response.status == 401
    assert not _bag_exists('foo')

    headers = { 'Cookie': ADMIN_COOKIE }
    headers.update(default_headers)
    response, content = _req('POST', '/wikis', urlencode(data), headers=headers)
    assert response.status == 303
    assert response['location'] == '/foo'
    assert _bag_exists('foo')

    response, content = _req('GET', '/foo', headers={ 'Cookie': ADMIN_COOKIE })
    assert response.status == 302
    assert response['location'] == '/foo/index'

    response, content = _req('GET', '/bar')
    assert response.status == 404

    response, content = _req('GET', '/foo')
    assert response.status == 302
    assert response['location'].endswith('/challenge?tiddlyweb_redirect=%2Ffoo')

    headers = { 'Cookie': ADMIN_COOKIE }
    headers.update(default_headers)
    response, content = _req('POST', '/wikis', urlencode(data), headers=headers)
    assert response.status == 409

    data['wiki'] = 'wikis'
    response, content = _req('POST', '/wikis', urlencode(data), headers=headers)
    assert response.status == 409

    assert not _bag_exists('bar')

    data = { 'wiki': 'bar' }
    headers = { 'Cookie': ADMIN_COOKIE }
    headers.update(default_headers)
    response, content = _req('POST', '/wikis', urlencode(data), headers=headers)
    assert response.status == 303
    assert response['location'] == '/bar'
    assert _bag_exists('bar')

    response, content = _req('GET', '/bar')
    assert response.status == 302
    assert response['location'] == '/bar/index'

    # TODO: test special characters in names


def test_page_creation_and_modification():
    default_headers = { 'Content-Type': 'application/x-www-form-urlencoded' }
    data = {
        'wiki': 'foo',
        'title': 'Lipsum',
        'tags': 'foo, bar, baz',
        'text': 'lorem ipsum'
    }

    response, content = _req('POST', '/pages')
    assert response.status == 415

    response, content = _req('POST', '/pages', urlencode(data),
            headers=default_headers)
    assert response.status == 403
    assert not _tiddler_exists('Lipsum', 'foo')

    headers = { 'Cookie': ADMIN_COOKIE }
    headers.update(default_headers)
    response, content = _req('POST', '/pages', urlencode(data), headers=headers)
    assert response.status == 303
    assert response['location'] == '/foo/Lipsum'
    assert _tiddler_exists('Lipsum', 'foo')

    response, content = _req('GET', '/foo/Lipsum', headers=headers)
    assert response.status == 200
    assert response['content-type'] == 'text/html; charset=UTF-8'
    assert '<p>lorem ipsum</p>' in content
    assert '>foo</a>' in content
    assert '>bar</a>' in content
    assert '>baz</a>' in content

    data['text'] = 'lorem ipsum\ndolor *sit* amet'
    data['tags'] = 'hello,world'
    response, content = _req('POST', '/pages', urlencode(data), headers=headers)
    assert response.status == 303
    assert response['location'] == '/foo/Lipsum'

    response, content = _req('GET', '/foo/Lipsum', headers=headers)
    assert '<p>lorem ipsum\ndolor <em>sit</em> amet</p>' in content
    assert '>hello</a>' in content
    assert '>world</a>' in content


def test_errors():
    response, content = _req('GET', '/N/A')
    assert response.status == 404
    assert '<html>' in content
    assert 'not found' in content

    response, content = _req('POST', '/')
    assert response.status == 405
    assert '<html>' in content
    assert 'not allowed' in content

    response, content = _req('GET', '/~')
    assert response.status == 401
    assert '<html>' in content
    assert 'unauthorized' in content

    response, content = _req('POST', '/register')
    assert response.status == 415
    assert '<html>' in content
    assert 'unsupported' in content

    data = {
        'username': 'foo',
        'password': 'bar',
        'password_confirmation': 'baz'
    }
    headers = { 'Content-Type': 'application/x-www-form-urlencoded' }
    response, content = _req('POST', '/register', urlencode(data),
            headers=headers)
    assert response.status == 400
    assert '<html>' in content
    assert 'passwords do not match' in content

    data = {
        'username': 'admin',
        'password': 'foo',
        'password_confirmation': 'foo'
    }
    headers = { 'Content-Type': 'application/x-www-form-urlencoded' }
    response, content = _req('POST', '/register', urlencode(data),
            headers=headers)
    assert response.status == 409
    assert '<html>' in content
    assert 'username unavailable' in content


def test_static_assets():
    response, content = _req('GET', '/static')
    assert response.status == 404

    response, content = _req('GET', '/static/../tiddlywebconfig.py')
    assert response.status == 404

    response, content = _req('GET', '/static/pure.css')
    assert response.status == 200

    response, content = _req('GET', '/static/favicon.ico')
    assert response.status == 200

    # TODO
    #response, content = _req('GET', '/favicon.ico')
    #assert response.status == 200


def _tiddler_exists(title, bag_name):
    tiddler = Tiddler(title, bag_name)
    try:
        tiddler = STORE.get(tiddler)
        return True
    except NoTiddlerError:
        return False


def _bag_exists(bag_name):
    bag = Bag(bag_name)
    try:
        STORE.get(bag)
        return bag
    except NoBagError:
        return False
