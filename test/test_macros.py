from textwrap import dedent

from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.model.bag import Bag
from tiddlyweb.config import config as CONFIG
from tiddlyweb.web.util import make_cookie

from . import make_instance, req


def setup_module(module):
    instance = make_instance()
    module.STORE = instance['store']

    STORE.put(Bag('content'))
    STORE.put(Bag('alpha'))
    STORE.put(Bag('bravo'))

    tiddler = Tiddler('data', 'content')
    tiddler.type = 'text/x-markdown'
    tiddler.text = dedent("""
    lorem ipsum
    dolor sit amet

    {{macro:sorting}}@alpha

    {{macro:filtering}}@bravo
    """)
    STORE.put(tiddler)

    tiddler = Tiddler('sorting', 'alpha')
    tiddler.text = 'alert("init!");'
    STORE.put(tiddler)


def test_whitelisting():
    cookie = make_cookie('tiddlyweb_user', 'dummy', mac_key=CONFIG['secret'])

    # pre-whitelisting
    for cookie in [None, cookie]: # guest and auth'd user, respectively
        headers = { 'Cookie': cookie } if cookie else None
        response, content = req('GET', '/content/data', headers=headers)
        assert '<p>lorem ipsum\ndolor sit amet</p>' in content
        assert '<script src="/alpha/sorting"' not in content
        assert '<script src="/bravo/filtering"' not in content
        assert '{{macro:sorting}}@alpha' not in content
        assert '{{macro:filtering}}@bravo' not in content

    # create whitelist in user's home wiki
    STORE.put(Bag('dummy'))
    tiddler = Tiddler('_macros', 'dummy')
    tiddler.text = 'alpha/sorting'
    STORE.put(tiddler)

    response, content = req('GET', '/content/data',
            headers={ 'Cookie': cookie })
    assert '<p>lorem ipsum\ndolor sit amet</p>' in content
    assert '<script src="/alpha/sorting"' in content
    assert '<script src="/bravo/filtering"' not in content # page does not exist
    assert '{{macro:sorting}}@alpha' not in content
    assert '{{macro:filtering}}@bravo' not in content
