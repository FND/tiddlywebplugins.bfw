import os

from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.model.bag import Bag
from tiddlyweb.manage import handle

from . import make_instance, req, StreamCapture


def setup_module(module):
    instance = make_instance()
    module.STORE = instance['store']


def test_gitstore():
    gitdir = os.path.join(STORE.storage._root, '.git')
    assert os.path.isdir(gitdir)


def test_tagdex():
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
        tags = stream.read().splitlines()
        assert 'foo' in tags
        assert 'bar' in tags
