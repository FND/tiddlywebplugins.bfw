import sys
import os
import tempfile

import httplib2
import wsgi_intercept

import mangler

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


def make_instance():
    tmpdir = tempfile.mkdtemp()
    _initialize_app(tmpdir)
    store = get_store(CONFIG)

    # register admin user
    admin_cookie = make_cookie('tiddlyweb_user', 'admin',
            mac_key=CONFIG['secret'])
    data = { 'username': 'admin', 'password': 'secret' }
    data['password_confirmation'] = data['password']
    response, content = req('POST', '/register', urlencode(data),
            headers={ 'Content-Type': 'application/x-www-form-urlencoded' })

    return tmpdir, store, admin_cookie


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


def req(method, uri, body=None, **kwargs):
    http = httplib2.Http()
    http.follow_redirects = False
    return http.request('http://example.org:8001%s' % uri, method=method,
            body=body, **kwargs)
