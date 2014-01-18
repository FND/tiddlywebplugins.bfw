"""
default BFW configuration
"""

config = {
    'instance_pkgstores': ['tiddlywebplugins.bfw'],
    'server_store': ['tiddlywebplugins.gitstore', { 'store_root': 'store' }],
    'static_url_dir': 'static',
    'static_file_dir': ('tiddlywebplugins.bfw', 'assets'),
    'wikitext.type_render_map': {
        'text/x-markdown': 'tiddlywebplugins.markdown'
    },
    'markdown.extensions': (['markdown_checklist.extension'], {}),
    'markdown.wiki_link_base': ''
}
