import sys
import os
import shutil

from StringIO import StringIO

from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.model.bag import Bag
from tiddlyweb.manage import handle

from . import make_instance, req, StreamCapture


def setup_module(module):
    print "\n", "0" * 80, "init plugin integration"
    module.CWD = os.getcwd()
    module.TMPDIR, module.STORE, _ = make_instance()
    print "\n", "1" * 80, "created instance in %s from %s" % (TMPDIR, CWD)


def teardown_module(module):
    os.chdir(CWD)
    shutil.rmtree(TMPDIR)
    print "\n", "2" * 80, "removed instance in %s from %s" % (TMPDIR, os.getcwd())


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
        assert stream.read() == "foo\nbar\n"
