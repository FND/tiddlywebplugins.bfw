from tiddlyweb.web.util import encode_name

from .util import Link


RESOURCES = {
    'front page': '',
    'dashboard': '~',
    'wiki page': '%(wiki)s/%(page)s',
    'wiki index': '%(wiki)s/index', # required for links below
    'page editor': 'editor?page=%(wiki)s%%2F%(page)s',
    'global activity': 'history',
    'wiki activity': 'history/%(wiki)s',
    'page history': 'history/%(wiki)s/%(page)s',
    'help': 'help',
    'recent changes': lambda params: _recent_changes_uri(params),
    'wikis': 'wikis',
    'pages': 'pages',
    'tiddler': 'bags/%(bag)s/tiddlers/%(title)s',
    'tag': 'tags/%(tag)s',
    'register': 'register',
    'login': 'challenge/cookie_form'
}

LINKS = {
    'front page': ['front page', 'dashboard', 'recent changes', 'help'],
    'wiki page':  ['front page', 'dashboard', 'wiki index', 'recent changes',
            'page editor', 'help'],
    'recent changes': ['front page', 'dashboard', 'page history',
            'wiki activity', 'global activity']
}
LINKS['dashboard'] = LINKS['front page']
LINKS['help'] = LINKS['front page']
LINKS['page editor'] = ['wiki page' if item == 'page editor' else item for item
        in LINKS['wiki page']]


def nav(resource, environ, wiki=None, page=None):
    params = { 'wiki': wiki, 'page': page }
    params = { key: value for key, value in params.items() if value }
    for item in LINKS[resource]:
        yield Link(uri(item, environ, **params), item, item == resource)


def uri(resource, environ, **params):
    """
    generates the respective resource's URI

    `params` is used for placeholders
    """
    server_prefix = environ['tiddlyweb.config'].get('server_prefix', '')
    params = { key: encode_name(param) for key, param in params.items() }
    uri = RESOURCES[resource]
    if callable(uri):
        uri = uri(params)
    return '/'.join([server_prefix, uri % params])


def _recent_changes_uri(params):
    """
    determines the most specific recent changes resource available in the given
    context
    """
    if params.get('wiki'):
        if params.get('page'):
            return 'page history'
        return 'wiki activity'
    return 'global activity'
