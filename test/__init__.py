import sys
import os
import shutil

import httplib2
import wsgi_intercept

import mangler

from StringIO import StringIO
from urllib import urlencode
from wsgi_intercept import httplib2_intercept

from tiddlyweb.config import config as CONFIG
from tiddlyweb.util import merge_config
from tiddlyweb.web.serve import load_app
from tiddlyweb.web.util import make_cookie
from tiddlywebplugins.utils import get_store
from tiddlywebplugins.imaker import spawn

from tiddlywebplugins.bfw import instance
from tiddlywebplugins.bfw.config import config as init_config


INSTANCE = {}


def make_instance():
    if len(INSTANCE): # multiple instances in a single process are unsupported
        return INSTANCE

    tmpdir = os.path.abspath('tmp')
    if os.path.isdir(tmpdir):
        shutil.rmtree(tmpdir)
    os.mkdir(tmpdir)

    _initialize_app(tmpdir)
    store = get_store(CONFIG)

    # register admin user
    admin_cookie = make_cookie('tiddlyweb_user', 'admin',
            mac_key=CONFIG['secret'])
    data = { 'username': 'admin', 'password': 'secret' }
    data['password_confirmation'] = data['password']
    response, content = req('POST', '/register', urlencode(data),
            headers={ 'Content-Type': 'application/x-www-form-urlencoded' })

    INSTANCE['tmpdir'] = tmpdir
    INSTANCE['store'] = store
    INSTANCE['admin_cookie'] = admin_cookie
    return INSTANCE


def req(method, uri, body=None, **kwargs):
    http = httplib2.Http()
    http.follow_redirects = False
    return http.request('http://example.org:8001%s' % uri, method=method,
            body=body, **kwargs)


class StreamCapture(object):

    def __init__(self, stream='stdout'):
        self.stream = stream

    def __enter__(self):
        self.original = getattr(sys, self.stream)
        dummy = StringIO()
        setattr(sys, self.stream, dummy)
        return dummy

    def __exit__(self, type, value, traceback):
        setattr(sys, self.stream, self.original)


def _initialize_app(tmpdir): # XXX: side-effecty and inscrutable
    instance_dir = os.path.join(tmpdir, 'instance')

    spawn(instance_dir, init_config, instance)
    old_cwd = os.getcwd()
    os.chdir(instance_dir)
    # force loading of instance's `tiddlywebconfig.py`
    while old_cwd in sys.path:
        sys.path.remove(old_cwd)
    sys.path.insert(0, os.getcwd())
    merge_config(CONFIG, {}, reconfig=True) # XXX: should not be necessary!?

    CONFIG['server_host'] = {
        'scheme': 'http',
        'host': 'example.org',
        'port': '8001',
    }
    # TODO: test with server_prefix

    # add symlink to templates -- XXX: hacky, should not be necessary!?
    templates_path = instance.__file__.split(os.path.sep)[:-2] + ['templates']
    os.symlink(os.path.sep.join(templates_path), 'templates')

    httplib2_intercept.install()
    wsgi_intercept.add_wsgi_intercept('example.org', 8001, load_app)
