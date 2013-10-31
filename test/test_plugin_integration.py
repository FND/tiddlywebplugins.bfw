import sys
import shutil

from StringIO import StringIO

from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.model.bag import Bag
from tiddlyweb.manage import handle

from . import make_instance, req, StreamCapture


def setup_module(module):
    module.TMPDIR, module.STORE, _ = make_instance()


def teardown_module(module):
    pass #shutil.rmtree(TMPDIR)


def test_dummy():
    assert True


def no_test_tagdex():
    bag = Bag('snippets')
    STORE.put(bag)

    tiddler = Tiddler('index', 'snippets')
    tiddler.text = 'lipsum'
    tiddler.tags = ['foo', 'bar']
    STORE.put(tiddler)

    response, content = req('GET', '/tags/foo')
    assert response.status == 200

    response, content = req('GET', '/tags/bar')
    assert response.status == 200

    with StreamCapture('stdout') as stream:
        handle(['', 'tags'])

        stream.seek(0)
        assert stream.read() == "foo\nbar\n"
