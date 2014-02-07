from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.model.bag import Bag

from tiddlywebplugins.bfw.commands import recent_changes

from . import make_instance


def setup_module(module):
    instance = make_instance()
    module.STORE = instance['store']

    STORE.put(Bag('alpha'))
    STORE.put(Bag('bravo'))

    tiddlers = [
        ('alpha', 'Hello World', ['* foo\n* bar\n', '* baz\n']),
        ('bravo', 'abc', ['...']),
        ('alpha', 'Lipsum', ['lorem ipsum\n', 'dolor sit amet\n']),
        ('bravo', 'abc', ['XXX'])
    ]
    for bag, title, fragments in tiddlers:
        tiddler = Tiddler(title, bag)
        tiddler.text = ''
        for fragment in fragments:
            tiddler.text += fragment
            STORE.put(tiddler)


def test_global():
    expected = [
        ('alpha', 'Hello World', '* foo\n* bar\n'),
        ('alpha', 'Hello World', '* foo\n* bar\n* baz\n'),
        ('bravo', 'abc', '...'),
        ('alpha', 'Lipsum', 'lorem ipsum\n'),
        ('alpha', 'Lipsum', 'lorem ipsum\ndolor sit amet\n'),
        ('bravo', 'abc', 'XXX')
    ]
    assert list(recent_changes(STORE)) == expected
