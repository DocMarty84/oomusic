# -*- coding: utf-8 -*-

import random

from lxml import etree

from odoo import http
from odoo.http import request

from .common import SubsonicREST


def _uniquify_list(seq):
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]


class MusicSubsonicListing(http.Controller):
    @http.route(
        ["/rest/getAlbumList.view", "/rest/getAlbumList"],
        type="http",
        auth="public",
        csrf=False,
        methods=["GET", "POST"],
    )
    def getAlbumList(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        FolderObj = request.env["oomusic.folder"]

        list_type_accepted = [
            "random",
            "newest",
            "frequent",
            "recent",
            "starred",
            "highest",
            "alphabeticalByName",
            "alphabeticalByArtist",
            "byYear",
            "byGenre",
        ]

        list_type = kwargs.get("type")
        if not list_type:
            return rest.make_error(
                code="10", message='Required string parameter "type" is not present'
            )
        if list_type not in list_type_accepted:
            return rest.make_error(code="0", message="Invalid list type: %s" % list_type)

        fromYear = kwargs.get("fromYear")
        toYear = kwargs.get("toYear")
        if list_type == "byYear" and (not fromYear or not toYear):
            return rest.make_error(
                code="10", message='Required string parameter "fromYear" or "toYear" is not present'
            )

        genre = kwargs.get("genre")
        if list_type == "byGenre" and not genre:
            return rest.make_error(
                code="10", message='Required string parameter "genre" is not present'
            )

        folderId = kwargs.get("musicFolderId")
        if folderId:
            folder = request.env["oomusic.folder"].browse([int(folderId)])
            if not folder.exists():
                return rest.make_error(code="70", message="Folder not found")

        size = min(int(kwargs.get("size", 10)), 500)
        offset = int(kwargs.get("offset", 0))

        # Build domain
        domain = [("id", "child_of", int(folderId))] if folderId else []
        if list_type == "starred":
            domain += [("star", "=", "1")]

        # Search for albums
        if list_type == "random":
            folder_ids = FolderObj.search(domain).ids
            if folder_ids:
                folder_ids = random.sample(folder_ids, min(size, len(folder_ids)))

            folders = FolderObj.browse(folder_ids)

        elif list_type == "newest":
            folders = FolderObj.search(domain, order="create_date desc")

        elif list_type == "recent":
            q_select = """
                SELECT t.folder_id FROM oomusic_track t
                JOIN oomusic_preference AS p ON t.id = p.res_id
            """
            q_where = """
                WHERE p.user_id = %s AND p.last_play IS NOT NULL AND p.res_model = \'oomusic.track\'
            """ % (
                request.env.user.id
            )
            if folderId:
                q_where += "AND t.root_folder_id = %s " % (folderId)
            q_order = "ORDER BY p.last_play desc;"
            query = q_select + q_where + q_order
            request.env.cr.execute(query)
            res = request.env.cr.fetchall()

            folder_ids = _uniquify_list([r[0] for r in res if r[0] is not None])
            folders = FolderObj.browse(folder_ids)

        elif list_type == "frequent":
            q_select = """
                SELECT t.folder_id FROM oomusic_track t
                JOIN oomusic_preference AS p ON t.id = p.res_id
            """
            q_where = """
                WHERE p.user_id = %s AND p.play_count > 0 AND p.res_model = \'oomusic.track\'
            """ % (
                request.env.user.id
            )
            if folderId:
                q_where += "AND t.root_folder_id = %s " % (folderId)
            q_order = "ORDER BY p.play_count desc;"
            query = q_select + q_where + q_order
            request.env.cr.execute(query)
            res = request.env.cr.fetchall()

            folder_ids = _uniquify_list([r[0] for r in res if r[0] is not None])
            folders = FolderObj.browse(folder_ids)

        elif list_type == "alphabeticalByName":
            folders = FolderObj.search(domain, order="path")

        elif list_type == "alphabeticalByArtist":
            folders = FolderObj.search(domain, order="parent_id")

        else:
            folders = FolderObj.search(domain)

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        xml_folder_list = rest.make_AlbumList()
        root.append(xml_folder_list)

        if folders:
            min_val = min(offset, len(folders))
            max_val = min_val + size
            for folder in folders[min_val:max_val]:
                xml_folder = rest.make_Child_folder(folder, tag_name="album")
                xml_folder_list.append(xml_folder)

        return rest.make_response(root)

    @http.route(
        ["/rest/getAlbumList2.view", "/rest/getAlbumList2"],
        type="http",
        auth="public",
        csrf=False,
        methods=["GET", "POST"],
    )
    def getAlbumList2(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        AlbumObj = request.env["oomusic.album"]

        list_type_accepted = [
            "random",
            "newest",
            "frequent",
            "recent",
            "starred",
            "alphabeticalByName",
            "alphabeticalByArtist",
            "byYear",
            "byGenre",
        ]

        list_type = kwargs.get("type")
        if not list_type:
            return rest.make_error(
                code="10", message='Required string parameter "type" is not present'
            )
        if list_type not in list_type_accepted:
            return rest.make_error(code="0", message="Invalid list type: %s" % list_type)

        fromYear = kwargs.get("fromYear")
        toYear = kwargs.get("toYear")
        if list_type == "byYear" and (not fromYear or not toYear):
            return rest.make_error(
                code="10", message='Required string parameter "fromYear" or "toYear" is not present'
            )

        genre = kwargs.get("genre")
        if list_type == "byGenre" and not genre:
            return rest.make_error(
                code="10", message='Required string parameter "genre" is not present'
            )

        folderId = kwargs.get("musicFolderId")
        if folderId:
            folder = request.env["oomusic.folder"].browse([int(folderId)])
            if not folder.exists():
                return rest.make_error(code="70", message="Folder not found")

        size = min(int(kwargs.get("size", 10)), 500)
        offset = int(kwargs.get("offset", 0))

        # Build domain
        domain = [("folder_id", "child_of", int(folderId))] if folderId else []
        if list_type == "byYear":
            if int(fromYear) > int(toYear):
                domain += [("year", ">=", toYear), ("year", "<=", fromYear)]
            else:
                domain += [("year", ">=", fromYear), ("year", "<=", toYear)]
        elif list_type == "byGenre":
            domain += [("genre_id.name", "ilike", genre)]
        elif list_type == "starred":
            domain += [("star", "=", "1")]

        # Search for albums
        if list_type == "random":
            album_ids = AlbumObj.search(domain).ids
            if album_ids:
                album_ids = random.sample(album_ids, min(size, len(album_ids)))

            albums = AlbumObj.browse(album_ids)

        elif list_type == "newest":
            albums = AlbumObj.search(domain, order="create_date desc")

        elif list_type == "recent":
            q_select = """
                SELECT t.album_id FROM oomusic_track t
                JOIN oomusic_preference AS p ON t.id = p.res_id
            """
            q_where = """
                WHERE p.user_id = %s AND p.last_play IS NOT NULL AND p.res_model = \'oomusic.track\'
            """ % (
                request.env.user.id
            )
            if folderId:
                q_where += "AND t.root_folder_id = %s " % (folderId)
            q_order = "ORDER BY p.last_play desc;"
            query = q_select + q_where + q_order
            request.env.cr.execute(query)
            res = request.env.cr.fetchall()

            album_ids = _uniquify_list([r[0] for r in res if r[0] is not None])
            albums = AlbumObj.browse(album_ids)

        elif list_type == "frequent":
            q_select = """
                SELECT t.album_id FROM oomusic_track t
                JOIN oomusic_preference AS p ON t.id = p.res_id
            """
            q_where = """
                WHERE p.user_id = %s AND p.play_count > 0 AND p.res_model = \'oomusic.track\'
            """ % (
                request.env.user.id
            )
            if folderId:
                q_where += "AND t.root_folder_id = %s " % (folderId)
            q_order = "ORDER BY p.play_count desc;"
            query = q_select + q_where + q_order
            request.env.cr.execute(query)
            res = request.env.cr.fetchall()

            album_ids = _uniquify_list([r[0] for r in res if r[0] is not None])
            albums = AlbumObj.browse(album_ids)

        elif list_type == "alphabeticalByName":
            albums = AlbumObj.search(domain, order="name")

        elif list_type == "alphabeticalByArtist":
            albums = AlbumObj.search(domain, order="artist_id")

        elif list_type == "byYear":
            if int(fromYear) > int(toYear):
                albums = AlbumObj.search(domain, order="year desc")
            else:
                albums = AlbumObj.search(domain, order="year")

        else:
            albums = AlbumObj.search(domain)

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        xml_album_list = rest.make_AlbumList2()
        root.append(xml_album_list)

        if albums:
            min_val = min(offset, len(albums))
            max_val = min_val + size
            for album in albums[min_val:max_val]:
                xml_album = rest.make_AlbumID3(album)
                xml_album_list.append(xml_album)

        return rest.make_response(root)

    @http.route(
        ["/rest/getRandomSongs.view", "/rest/getRandomSongs"],
        type="http",
        auth="public",
        csrf=False,
        methods=["GET", "POST"],
    )
    def getRandomSongs(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        TrackObj = request.env["oomusic.track"]

        fromYear = kwargs.get("fromYear")
        toYear = kwargs.get("toYear")
        genre = kwargs.get("genre")

        folderId = kwargs.get("musicFolderId")
        if folderId:
            folder = request.env["oomusic.folder"].browse([int(folderId)])
            if not folder.exists():
                return rest.make_error(code="70", message="Folder not found")

        size = min(int(kwargs.get("size", 10)), 500)

        # Build domain
        domain = [("id", "child_of", int(folderId))] if folderId else []
        if fromYear:
            domain += [("year", ">=", fromYear)]
        if toYear:
            domain += [("year", "<=", toYear)]
        if genre:
            domain += [("genre_id.name", "ilike", genre)]

        track_ids = TrackObj.search(domain).ids
        if track_ids:
            track_ids = random.sample(track_ids, min(size, len(track_ids)))

        tracks = TrackObj.browse(track_ids)

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        xml_song_list = rest.make_listSongs("randomSongs")
        root.append(xml_song_list)

        for track in tracks:
            xml_song = rest.make_Child_track(track, tag_name="song")
            xml_song_list.append(xml_song)

        return rest.make_response(root)

    @http.route(
        ["/rest/getSongsByGenre.view", "/rest/getSongsByGenre"],
        type="http",
        auth="public",
        csrf=False,
        methods=["GET", "POST"],
    )
    def getSongsByGenre(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        TrackObj = request.env["oomusic.track"]

        genre = kwargs.get("genre")
        if not genre:
            return rest.make_error(
                code="10", message='Required str parameter "genre" is not present'
            )

        folderId = kwargs.get("musicFolderId")
        if folderId:
            folder = request.env["oomusic.folder"].browse([int(folderId)])
            if not folder.exists():
                return rest.make_error(code="70", message="Folder not found")

        size = min(int(kwargs.get("size", 10)), 500)
        offset = int(kwargs.get("offset", 0))

        # Build domain
        domain = [("id", "child_of", int(folderId))] if folderId else []
        domain += [("genre_id.name", "=", genre)]

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        xml_song_list = rest.make_listSongs("songsByGenre")
        root.append(xml_song_list)

        tracks = TrackObj.search(domain)

        if tracks:
            min_val = min(offset, len(tracks))
            max_val = min_val + size
            for track in tracks[min_val:max_val]:
                xml_song = rest.make_Child_track(track, tag_name="song")
                xml_song_list.append(xml_song)

        return rest.make_response(root)

    @http.route(
        ["/rest/getNowPlaying.view", "/rest/getNowPlaying"],
        type="http",
        auth="public",
        csrf=False,
        methods=["GET", "POST"],
    )
    def getNowPlaying(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        xml_song_list = rest.make_listSongs("nowPlaying")
        root.append(xml_song_list)

        # TODO support NowPlayingEntry

        return rest.make_response(root)

    @http.route(
        ["/rest/getStarred.view", "/rest/getStarred"],
        type="http",
        auth="public",
        csrf=False,
        methods=["GET", "POST"],
    )
    def getStarred(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        FolderObj = request.env["oomusic.folder"]
        TrackObj = request.env["oomusic.track"]

        folderId = kwargs.get("musicFolderId")
        if folderId:
            folder = request.env["oomusic.folder"].browse([int(folderId)])
            if not folder.exists():
                return rest.make_error(code="70", message="Folder not found")
        domain = [("id", "child_of", int(folderId))] if folderId else []

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        xml_starred_list = rest.make_listSongs("starred")
        root.append(xml_starred_list)

        folders = FolderObj.search(domain + [("star", "=", "1")])
        tracks = TrackObj.search(domain + [("star", "=", "1")])

        for folder in folders.sorted(lambda r: len(r.track_ids)):
            if not folder.track_ids:
                xml_folder = rest.make_Artist(folder)
            else:
                xml_folder = rest.make_Child_folder(folder, tag_name="album")
            xml_starred_list.append(xml_folder)

        for track in tracks:
            xml_song = rest.make_Child_track(track, tag_name="song")
            xml_starred_list.append(xml_song)

        return rest.make_response(root)

    @http.route(
        ["/rest/getStarred2.view", "/rest/getStarred2"],
        type="http",
        auth="public",
        csrf=False,
        methods=["GET", "POST"],
    )
    def getStarred2(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        ArtistObj = request.env["oomusic.artist"]
        AlbumObj = request.env["oomusic.album"]
        TrackObj = request.env["oomusic.track"]

        folderId = kwargs.get("musicFolderId")
        if folderId:
            folder = request.env["oomusic.folder"].browse([int(folderId)])
            if not folder.exists():
                return rest.make_error(code="70", message="Folder not found")
        domain = [("id", "child_of", int(folderId))] if folderId else []

        root = etree.Element("subsonic-response", status="ok", version=rest.version_server)
        xml_starred_list = rest.make_listSongs("starred2")
        root.append(xml_starred_list)

        artists = ArtistObj.search(domain + [("star", "=", "1")])
        albums = AlbumObj.search(domain + [("star", "=", "1")])
        tracks = TrackObj.search(domain + [("star", "=", "1")])

        for artist in artists:
            xml_artist = rest.make_ArtistID3(artist)
            xml_starred_list.append(xml_artist)

        for album in albums:
            xml_album = rest.make_AlbumID3(album)
            xml_starred_list.append(xml_album)

        for track in tracks:
            xml_song = rest.make_Child_track(track, tag_name="song")
            xml_starred_list.append(xml_song)

        return rest.make_response(root)
