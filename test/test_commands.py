import os
import shutil

from pytest import raises

from tiddlyweb.manage import handle

from . import make_instance, req, StreamCapture


def setup_module(module):
    print "\n", "0" * 80, "init commands"
    module.CWD = os.getcwd()
    module.TMPDIR, _, _ = make_instance()
    print "\n", "1" * 80, "created instance in %s from %s" % (TMPDIR, CWD)


def teardown_module(module):
    os.chdir(CWD)
    shutil.rmtree(TMPDIR)
    print "\n", "2" * 80, "removed instance in %s from %s" % (TMPDIR, os.getcwd())


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
