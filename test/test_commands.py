import os
import shutil

from pytest import raises

from tiddlyweb.manage import handle

from . import make_instance, req, StreamCapture


def setup_module(module):
    module.TMPDIR, _, _ = make_instance()


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
