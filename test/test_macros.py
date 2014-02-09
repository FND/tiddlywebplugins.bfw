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
    STORE.put(Bag('macros'))

    tiddler = Tiddler('data', 'content')
    tiddler.type = 'text/x-markdown'
    tiddler.text = dedent("""
    lorem ipsum
    dolor sit amet

    {{macro:augmentor}}@macros
    """)
    STORE.put(tiddler)

    tiddler = Tiddler('augmentor', 'macros')
    tiddler.text = 'alert("init!");'
    STORE.put(tiddler)


def test_whitelisting():
    cookie = make_cookie('tiddlyweb_user', 'dummy', mac_key=CONFIG['secret'])
    for cookie in [None, cookie]: # guest and auth'd user, respectively
        headers = { 'Cookie': cookie } if cookie else None
        response, content = req('GET', '/content/data', headers=headers)
        assert '<p>lorem ipsum\ndolor sit amet</p>' in content
        assert '<script src="/macros/augmentor"' not in content
        assert '{{macro:augmentor}}@macros' not in content

    # create whitelist
    STORE.put(Bag('dummy'))
    tiddler = Tiddler('_macros', 'dummy')
    tiddler.text = 'macros/augmentor'
    STORE.put(tiddler)

    response, content = req('GET', '/content/data',
            headers={ 'Cookie': cookie })
    assert '<p>lorem ipsum\ndolor sit amet</p>' in content
    assert '<script src="/macros/augmentor"' in content
    assert '{{macro:augmentor}}@macros' not in content
