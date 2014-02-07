from StringIO import StringIO

from dulwich.patch import write_tree_diff
from dulwich.repo import Repo


def recent_changes(store, wiki=None, page=None, max_entries=20):
    repo = Repo(store.storage._root) # NB: intentionally breaks encapsulation

    count = 0
    previous = None
    for entry in repo.get_walker():
        count += 1
        if max_entries and count > max_entries:
            break

        commit = entry.commit
        current = commit.tree
        if previous:
            yield _entry(repo, commit, current, previous)
        previous = current


def _entry(repo, commit, current, previous): # TODO: rename, document
    stream = StringIO()
    write_tree_diff(stream, repo.object_store, previous, current)
    return {
        'author': commit.author,
        'timestamp': commit.author_time, # XXX: ignores timezone
        'message': commit.message,
        'diff': stream.getvalue(),
        'wiki': None, # TODO
        'page': None # TODO
    }
