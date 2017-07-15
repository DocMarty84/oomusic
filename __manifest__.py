# -*- coding: utf-8 -*-
{
    'name': 'OOMusic',
    'author': 'Nicolas Martinelli',
    'category': 'Uncategorized',
    'summary': 'Music streaming module',
    'website': 'http://koozic.net/',
    'version': '0.1',
    'description': """
Music Collection
================

        """,
    'depends': [
        'base',
        'web',
        'web_tour',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/oomusic_security.xml',

        'views/oomusic_menu_views.xml',
        'views/oomusic_album_views.xml',
        'views/oomusic_artist_views.xml',
        'views/oomusic_converter_views.xml',
        'views/oomusic_folder_views.xml',
        'views/oomusic_genre_views.xml',
        'views/oomusic_playlist_views.xml',
        'views/oomusic_track_views.xml',
        'views/oomusic_suggestion_views.xml',
        'views/oomusic_transcoder_views.xml',
        'views/oomusic.xml',

        'data/oomusic_data.xml',
        'data/oomusic_artist_data.xml',
        'data/oomusic_converter_data.xml',
        'data/oomusic_folder_data.xml',
        'data/oomusic_format_data.xml',
        'data/oomusic_lastfm_data.xml',
        'data/oomusic_playlist_data.xml',
        'data/oomusic_track_data.xml',
        'data/oomusic_transcoder_data.xml',
    ],
    'demo': [
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': True,
    'license': 'Other OSI approved licence',
}
