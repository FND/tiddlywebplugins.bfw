import os

from pytest import raises

from tiddlyweb.manage import handle

from . import make_instance, StreamCapture


def setup_module(module):
    instance = make_instance()
    module.TMPDIR = instance['tmpdir']


def test_assetcopy():
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
