"""
basic structure and contents of a BFW
"""

instance_config = {
    'system_plugins': ['tiddlywebplugins.bfw'],
    'twanager_plugins': ['tiddlywebplugins.bfw']
}

store_structure = {
    'users': {
        'bfw': {} # not to be used as regular user
    },
    'bags': {
        'meta': {
            'desc': 'meta',
            'policy': {
                'owner': 'bfw',
                'read': [],
                'write': ['R:ADMIN'],
                'create': ['R:ADMIN'],
                'delete': ['R:ADMIN'],
                'manage': ['R:ADMIN']
            }
        }
    }
}

store_contents = {
    'meta': ['contents/meta.recipe']
}
