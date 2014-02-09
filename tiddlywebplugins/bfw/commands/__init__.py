import re

from StringIO import StringIO

from dulwich.patch import write_tree_diff
from dulwich.repo import Repo

from tiddlyweb.fixups import unquote


page_path_pattern = re.compile(r'^bags/([^/]+)/tiddlers/([^/]+)$')


def recent_changes(store, wiki=None, page=None, max_entries=20):
    repo = Repo(store.storage._root) # NB: intentionally breaks encapsulation

    count = 0
    previous = None
    for entry in repo.get_walker():
        if max_entries and count > max_entries:
            break

        commit = entry.commit
        current = commit.tree
        if previous:
            entry = _entry(repo, commit, current, previous)
            if entry:
                yield entry

        previous = current
        count += 1


def _entry(repo, commit, current, previous): # TODO: rename, document
    wiki, page = _extract_page_info(repo, previous, current)
    if not page:
        return

    stream = StringIO()
    write_tree_diff(stream, repo.object_store, previous, current) # XXX: expensive, unnecessary

    return {
        'author': commit.author,
        'timestamp': commit.author_time, # XXX: ignores timezone
        'message': commit.message,
        'diff': stream.getvalue(),
        'wiki': wiki,
        'page': page
    }


def _extract_page_info(repo, previous, current):
    changes = repo.object_store.tree_changes(previous, current)
    for (oldpath, newpath), _, _ in changes:
        path = newpath or oldpath
        matches = page_path_pattern.match(path)
        if matches:
            wiki, page = [unquote(name) for name in matches.groups()]
            if page != '.gitkeep': # XXX: special-casing; breaks encapsulation
                return wiki, page # XXX: premature?
    return None, None
