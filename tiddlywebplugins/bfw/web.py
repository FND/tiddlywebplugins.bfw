import os
import mimetypes

from httpexceptor import HTTP302, HTTP400, HTTP401, HTTP404, HTTP409

from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.model.bag import Bag
from tiddlyweb.model.user import User
from tiddlyweb.model.policy import Policy, UserRequiredError, ForbiddenError
from tiddlyweb.wikitext import render_wikitext
from tiddlyweb.store import NoTiddlerError, NoBagError, NoUserError
from tiddlyweb.web.util import get_route_value, make_cookie

from tiddlywebplugins.logout import logout as logout_handler
from tiddlywebplugins.templates import get_template

from .routing import nav, uri
from .util import ensure_form_submission


BLACKLIST = ['bags', 'recipes', 'wikis', 'pages', '~', 'register', 'logout'] # XXX: too manual, hard to keep in sync


def frontpage(environ, start_response):
    username = environ['tiddlyweb.usersign']['name']

    tiddler = Tiddler('index', 'meta')
    store = environ['tiddlyweb.store']
    try:
        tiddler = store.get(tiddler)
    except NoTiddlerError: # this should never occur
        pass

    uris = None if username != 'GUEST' else {
        'register': uri('register', environ),
        'login': uri('login', environ)
    }
    return _render_template(environ, start_response, 'frontpage.html',
            contents=render_wikitext(tiddler, environ),
            nav=nav('front page', environ), uris=uris)


def dashboard(environ, start_response):
    current_user = environ['tiddlyweb.usersign']
    username = current_user['name']
    if username == 'GUEST':
        raise HTTP401('unauthorized')

    store = environ['tiddlyweb.store']

    wikis = []
    for bag in store.list_bags():
        try:
            _, bag = _ensure_wiki_readable(environ, bag.name)
            wiki_uri = uri('wiki index', environ, wiki=bag.name)
            try:
                bag.policy.allows(current_user, 'write')
                writable = True
            except ForbiddenError, exc:
                writable = False
            wikis.append({ 'name': bag.name, 'uri': wiki_uri,
                    'writable': writable })
        except ForbiddenError, exc:
            pass

    tiddler = Tiddler('index', username)
    try:
        tiddler = store.get(tiddler)
    except NoTiddlerError: # this should never occur
        pass

    uris = {
        'create_wiki': uri('wikis', environ),
        'create_page': uri('pages', environ)
    }
    return _render_template(environ, start_response, 'dashboard.html',
            user=username, wikis=wikis, nav=nav('dashboard', environ),
            uris=uris, contents=render_wikitext(tiddler, environ))


def wiki_index(environ, start_response):
    wiki_name, _ = _ensure_wiki_readable(environ)
    raise HTTP302(uri('wiki index', environ, wiki=wiki_name))


def wiki_page(environ, start_response):
    wiki_name, bag = _ensure_wiki_readable(environ)

    page_name = get_route_value(environ, 'page_name')
    tiddler = Tiddler(page_name, bag.name)
    try:
        tiddler = bag.store.get(tiddler)
    except NoTiddlerError:
        raise HTTP302(uri('page editor', environ, wiki=wiki_name,
                page=page_name))

    title = wiki_name if page_name == 'index' else page_name # XXX: undesirable?
    tags = [(tag, uri('tag', environ, tag=tag)) for tag in sorted(tiddler.tags)]
    uris = {
        'edit': uri('page editor', environ, wiki=wiki_name, page=page_name),
        'source': uri('tiddler', environ, bag=wiki_name, title=page_name)
    }

    return _render_template(environ, start_response, 'wiki_page.html',
            title=title, page_title=page_name, uris=uris, tags=tags,
            nav=nav('wiki page', environ, wiki=wiki_name, page=page_name),
            contents=render_wikitext(tiddler, environ))


def page_editor(environ, start_response):
    page = environ['tiddlyweb.query']['page'][0] # TODO: guard against missing parameter
    wiki_name, page_name = page.split('/') # TODO: validate
    _, bag = _ensure_wiki_readable(environ, wiki_name)

    tiddler = Tiddler(page_name, bag.name)
    try:
        tiddler = bag.store.get(tiddler)
        msg = None
    except NoTiddlerError:
        msg = '"%s" does not exist yet in wiki "%s"' % (page_name, wiki_name)

    uris = {
        'put_page': uri('pages', environ)
    }
    return _render_template(environ, start_response, 'editor.html', uris=uris,
            title=page, wiki_name=wiki_name, page_title=page_name,
            nav=nav('page editor', environ, wiki=wiki_name, page=page_name),
            tagstr=', '.join(tiddler.tags), contents=tiddler.text,
            notification=msg)


@ensure_form_submission
def create_wiki(environ, start_response):
    username = environ['tiddlyweb.usersign']['name']
    if username == 'GUEST':
        raise HTTP401('unauthorized')

    wiki_name = environ['tiddlyweb.query']['wiki'][0] # TODO: validate
    private = environ['tiddlyweb.query'].get('private', [''])[0] == '1'

    if wiki_name in BLACKLIST:
        raise HTTP409('wiki name unavailable')

    _create_wiki(environ['tiddlyweb.store'], wiki_name, username, private)

    wiki_uri = uri('wiki index', environ, wiki=wiki_name).encode('UTF-8') # XXX: should include host!?
    start_response('303 See Other', [('Location', wiki_uri)])
    return ['']


@ensure_form_submission
def put_page(environ, start_response):
    wiki_name, title, tags, text = [environ['tiddlyweb.query'][param][0]
            for param in ['wiki', 'title', 'tags', 'text']]
    # TODO: validate title
    tags = [tag.strip() for tag in tags.split(',')]
    # TODO: parameter to only allow creation (for use in user home's quick creation UI)

    store = environ['tiddlyweb.store']
    bag = _ensure_bag_exists(wiki_name, store)

    bag.policy.allows(environ['tiddlyweb.usersign'], 'create')

    tiddler = Tiddler(title, bag.name)
    tiddler.type = 'text/x-markdown'
    tiddler.tags = tags
    tiddler.text = text
    store.put(tiddler)

    page_uri = uri('wiki page', environ, wiki=wiki_name, page=title).encode('UTF-8') # XXX: should include host!?
    start_response('303 See Other', [('Location', page_uri)])
    return ['']


@ensure_form_submission
def register_user(environ, start_response):
    username, password, confirmation = [environ['tiddlyweb.query'][param][0] for
            param in ('username', 'password', 'password_confirmation')]

    user = User(username)
    store = environ['tiddlyweb.store']
    try:
        store.get(user)
        available = False
    except NoUserError:
        available = username not in BLACKLIST
    if not available:
        raise HTTP409('username unavailable')

    if not password == confirmation:
        raise HTTP400('passwords do not match')

    _create_wiki(store, username, username, private=True)

    user.set_password(password)
    store.put(user)

    index = Tiddler('index', username)
    index.type = 'text/x-markdown'
    index.text = "Welcome to %s's personal wiki." % username
    store.put(index)

    root_uri = uri('front page', environ)

    cookie = make_cookie('tiddlyweb_user', user.usersign, path=root_uri,
            mac_key=environ['tiddlyweb.config']['secret'],
            expires=environ['tiddlyweb.config'].get('cookie_age', None))

    start_response('303 See Other',
            [('Set-Cookie', cookie), ('Location', root_uri.encode('UTF-8'))])
    return ['']


def logout(environ, start_response):
    environ['tiddlyweb.query']['tiddlyweb_redirect'] = [uri('front page', environ)]
    return logout_handler(environ, start_response)


def _render_template(environ, start_response, name, status='200 OK', headers={},
        **data):
    template = get_template(environ, name)
    if not 'Content-Type' in headers: # XXX: case-sensitivity conflicts?
        headers['Content-Type'] = 'text/html; charset=UTF-8'
    start_response(status, headers.items())
    return template.generate(**data)


def _create_wiki(store, name, owner, private):
    bag = Bag(name)
    try:
        store.get(bag)
        raise HTTP409('wiki name unavailable')
    except NoBagError:
        pass

    read_constraint = [owner] if private else None
    bag.policy = Policy(read=read_constraint, write=[owner], create=[owner],
            delete=[owner], manage=[owner]) # XXX: too limiting!?
    store.put(bag)


def _ensure_wiki_readable(environ, wiki_name=None):
    current_user = environ['tiddlyweb.usersign']
    if not wiki_name: # XXX: bad API!?
        wiki_name = get_route_value(environ, 'wiki_name')

    store = environ['tiddlyweb.store']
    bag = _ensure_bag_exists(wiki_name, store)

    bag.policy.allows(current_user, 'read')

    return wiki_name, bag


def _ensure_bag_exists(bag_name, store):
    bag = Bag(bag_name)
    try:
        bag = store.get(bag)
    except NoBagError:
        raise HTTP404('wiki not found')

    return bag
