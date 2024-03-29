# -*- coding: utf-8 -*-

import json
import random

from odoo import api, fields, models
from odoo.exceptions import MissingError
from odoo.tools.safe_eval import safe_eval


class MusicPlaylist(models.Model):
    _name = "oomusic.playlist"
    _description = "Music Playlist"
    _inherit = ["oomusic.download.mixin"]

    def _default_current(self):
        return not bool(self.env["oomusic.playlist"].search([("current", "=", True)]))

    name = fields.Char("Name", required="1")
    user_id = fields.Many2one(
        "res.users",
        string="User",
        index=True,
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.user,
    )
    comment = fields.Char("Comment")
    current = fields.Boolean("Current", default=lambda self: self._default_current(), copy=False)
    audio_mode = fields.Selection(
        [("standard", "Standard"), ("raw", "No Transcoding"), ("norm", "Normalize")],
        "Audio Mode",
        default="standard",
        help="- Standard: regular transcoding of the files.\n"
        "- No Transcoding: do not transcode audio files. It decreases the server load, "
        "at the cost of a higher network usage.\n"
        "- Normalize: normalize playlist loudness thanks to the EBU R128 normalization. It "
        "requires FFmpeg >=3.2.1 which includes by default the appropriate library "
        "(libebur128).\n"
        "Transcoding will be significantly slower when activated, implying larger gaps between"
        " songs.",
    )
    audio = fields.Selection(
        [("html", "HTML5 Audio"), ("web", "Web Audio API")],
        "Audio API",
        default="html",
        help="API used for audio playback.\n"
        "- HTML5 Audio: no need to download the full file before starting the playback.\n"
        "- Web Audio API: need to download the full file before starting the playback. More \n"
        "reliable than HTML5, but longer gaps between tracks.",
    )
    playlist_line_ids = fields.One2many(
        "oomusic.playlist.line", "playlist_id", string="Tracks", copy=True
    )
    album_id = fields.Many2one(
        "oomusic.album",
        string="Add Album Tracks",
        store=False,
        help="Encoding help. When selected, the associated album tracks are added to the playlist.",
    )
    artist_id = fields.Many2one(
        "oomusic.artist",
        string="Add Artist Tracks",
        store=False,
        help="Encoding help. When selected, the associated artist tracks are added to the playlist.",
    )
    dynamic = fields.Boolean(
        "Dynamic",
        default=False,
        help="If activated, tracks will be automatically added based on the Smart Playlist.",
    )
    dynamic_max_qty = fields.Integer(
        "Maximum Tracks",
        default=0,
        help="If set, the oldest tracks of a dynamic playlist are automatically removed. "
        "This way, they can be added again.",
    )
    smart_playlist = fields.Selection(
        [
            ("rnd", "Random Tracks"),
            ("played", "Already Played"),
            ("not_played", "Never Played"),
            ("most_played", "Most Played"),
            ("last_listened", "Last Listened"),
            ("recent", "Recent"),
            ("favorite", "Favorites"),
            ("best_rated", "Best Rated"),
            ("worst_rated", "Worst Rated"),
            ("custom", "Custom"),
        ],
        "Smart Playlist",
    )
    smart_playlist_qty = fields.Integer("Quantity To Add", default=20)
    smart_custom_domain = fields.Char("Custom Domain")
    smart_custom_order = fields.Char("Custom Order")

    def _add_tracks(self, tracks, onchange=False):
        # Set starting sequence
        seq = self.playlist_line_ids[-1:].sequence or 10

        playlist_line = self.env["oomusic.playlist.line"]
        playlist_line_list = []
        for track in tracks:
            seq = seq + 1
            data = {
                "sequence": seq,
                "track_id": track.id,
                "user_id": self.user_id.id,
            }
            if onchange:
                # This will keep the line displayed in a (more or less) correct order while they
                # are added
                playlist_line_list.append(playlist_line.new(data))
            else:
                data["playlist_id"] = self.id
                playlist_line_list.append(data)

        if onchange:
            ids = [pl.id for pl in playlist_line_list]
            playlist_line = playlist_line.browse(ids)
            self.playlist_line_ids += playlist_line
        else:
            playlist_line = playlist_line.create(playlist_line_list)
        return playlist_line

    def _get_track_ids(self):
        return self.playlist_line_ids.mapped("track_id")

    @api.onchange("album_id")
    def _onchange_album_id(self):
        self._add_tracks(self.album_id.track_ids, onchange=True)
        self.album_id = False
        return {}

    @api.onchange("artist_id")
    def _onchange_artist_id(self, onchange=True):
        self._add_tracks(self.artist_id.track_ids, onchange=True)
        self.artist_id = False
        return {}

    @api.onchange("audio")
    def _onchange_audio(self):
        self.audio_mode = "raw" if self.audio == "web" else "standard"

    def action_purge(self):
        # Use sudo to skip ir.rules checks: if we can read the lines it means we can deleted them.
        self.env["oomusic.playlist.line"].search([("playlist_id", "in", self.ids)]).sudo().unlink()

    def action_current(self):
        self.ensure_one()
        self.env["oomusic.playlist"].search([("current", "=", True)]).current = False
        self.current = True

    def action_add_to_playlist(self):
        for playlist in self:
            if playlist.smart_playlist_qty < 1:
                playlist.smart_playlist_qty = 20
            tracks = getattr(self, "_smart_{}".format(playlist.smart_playlist))()
            playlist._add_tracks(tracks)

    def action_remove_duplicate(self):
        for playlist in self:
            track_ids = set([])
            lines_to_unlink = self.env["oomusic.playlist.line"]
            for playlist_line_id in playlist.playlist_line_ids:
                if playlist_line_id.track_id.id in track_ids:
                    lines_to_unlink |= playlist_line_id
                else:
                    track_ids.add(playlist_line_id.track_id.id)
        lines_to_unlink.unlink()

    def action_play(self):
        if len(self) != 1 or not self.playlist_line_ids:
            return True
        line = False
        if self.dynamic:
            line = self.playlist_line_ids.filtered("last_play")[-1:]
        if not line:
            line = self.playlist_line_ids[:1]
        return line.action_play()

    def _smart_rnd(self):
        current_tracks = self.playlist_line_ids.mapped("track_id")
        folder_sharing = (
            "inactive" if self.env.ref("oomusic.oomusic_track").sudo().perm_read else "active"
        )
        query = "SELECT id FROM oomusic_track "
        if current_tracks:
            query += "WHERE id NOT IN %s" % (tuple(current_tracks.ids + [0]),)
        if folder_sharing == "inactive":
            query += "{} user_id = {} ".format(
                "WHERE" if not current_tracks else "AND", self.env.uid
            )
        query += "ORDER BY RANDOM() "
        query += "LIMIT {}".format(self.smart_playlist_qty or 1)
        self.env.cr.execute(query)
        res = self.env.cr.fetchall()
        if not res:
            return self.env["oomusic.track"]

        track_ids = [r[0] for r in res]
        return self.env["oomusic.track"].browse(track_ids)

    def _smart_played(self):
        current_tracks = self.playlist_line_ids.mapped("track_id")
        return self.env["oomusic.track"].search(
            [("play_count", ">", 0), ("id", "not in", current_tracks.ids)],
            limit=self.smart_playlist_qty,
        )

    def _smart_not_played(self):
        current_tracks = self.playlist_line_ids.mapped("track_id")
        return self.env["oomusic.track"].search(
            [("play_count", "=", 0), ("id", "not in", current_tracks.ids)],
            limit=self.smart_playlist_qty,
        )

    def _smart_most_played(self):
        # order on a non-stored field is not supported, even if there is a search method. Therefore,
        # we directly search on oomusic.preference.
        current_tracks = self.playlist_line_ids.mapped("track_id")
        res_ids = [
            p["res_id"]
            for p in self.env["oomusic.preference"]
            .search(
                [
                    ("play_count", ">", 0),
                    ("res_model", "=", "oomusic.track"),
                    ("res_id", "not in", current_tracks.ids),
                ],
                limit=self.smart_playlist_qty,
                order="play_count DESC",
            )
            .read(["res_id"])
        ]
        return self.env["oomusic.track"].browse(res_ids)

    def _smart_last_listened(self):
        current_tracks = self.playlist_line_ids.mapped("track_id")
        res_ids = [
            p["res_id"]
            for p in self.env["oomusic.preference"]
            .search(
                [
                    ("last_play", "!=", False),
                    ("res_model", "=", "oomusic.track"),
                    ("res_id", "not in", current_tracks.ids),
                ],
                limit=self.smart_playlist_qty,
                order="last_play DESC",
            )
            .read(["res_id"])
        ]
        return self.env["oomusic.track"].browse(res_ids)

    def _smart_recent(self):
        current_tracks = self.playlist_line_ids.mapped("track_id")
        return self.env["oomusic.track"].search(
            [("id", "not in", current_tracks.ids)],
            limit=self.smart_playlist_qty,
            order="create_date DESC, " + self.env["oomusic.track"]._order,
        )

    def _smart_favorite(self):
        current_tracks = self.playlist_line_ids.mapped("track_id")
        return self.env["oomusic.track"].search(
            [("star", "=", "1"), ("id", "not in", current_tracks.ids)],
            limit=self.smart_playlist_qty,
        )

    def _smart_best_rated(self):
        current_tracks = self.playlist_line_ids.mapped("track_id")
        res_ids = [
            p["res_id"]
            for p in self.env["oomusic.preference"]
            .search(
                [("res_model", "=", "oomusic.track"), ("res_id", "not in", current_tracks.ids)],
                limit=self.smart_playlist_qty,
                order="rating DESC",
            )
            .read(["res_id"])
        ]
        return self.env["oomusic.track"].browse(res_ids)

    def _smart_worst_rated(self):
        current_tracks = self.playlist_line_ids.mapped("track_id")
        # By searching in the 'oomusic.preference' table, we miss the tracks not rated.
        res_ids = [
            p["res_id"]
            for p in self.env["oomusic.preference"]
            .search(
                [("res_model", "=", "oomusic.track"), ("res_id", "not in", current_tracks.ids)],
                limit=self.smart_playlist_qty,
                order="rating",
            )
            .read(["res_id"])
        ]
        return self.env["oomusic.track"].browse(res_ids)

    def _smart_custom(self):
        current_tracks = self.playlist_line_ids.mapped("track_id")
        if not self.smart_custom_order:
            tracks = self.env["oomusic.track"].search_read(
                domain=[("id", "not in", current_tracks.ids)] + safe_eval(self.smart_custom_domain),
                fields=["id"],
            )
            tracks_list = random.sample(tracks, min(self.smart_playlist_qty, len(tracks)))
        else:
            tracks = self.env["oomusic.track"].search_read(
                domain=[("id", "not in", current_tracks.ids)] + safe_eval(self.smart_custom_domain),
                fields=["id"],
                order=self.smart_custom_order,
                limit=self.smart_playlist_qty,
            )
            tracks_list = tracks
        return self.env["oomusic.track"].browse([t["id"] for t in tracks_list])

    def _update_dynamic(self):
        for playlist in self.filtered("dynamic"):
            if playlist.smart_playlist_qty != 1:
                playlist.smart_playlist_qty = 1

            played = playlist.playlist_line_ids.filtered("last_play")

            # Add a track if no more than 10 tracks already waiting
            if len(playlist.playlist_line_ids - played) < 10:
                tracks = getattr(self, "_smart_{}".format(playlist.smart_playlist))()
                playlist._add_tracks(tracks)

            # Resequence if user did not play the last track
            max_seq_last_play = max(x["sequence"] for x in played.read(["sequence"]))
            min_seq_not_play = min(
                x["sequence"] for x in (playlist.playlist_line_ids - played).read(["sequence"])
            )
            if max_seq_last_play > min_seq_not_play:
                offset = 0
                for i, line in enumerate(played):
                    line.write({"sequence": i})
                    offset = i + 1
                for i, line in enumerate(playlist.playlist_line_ids - played):
                    line.write({"sequence": i + offset})

            # Remove oldest lines if maximum size:
            if playlist.dynamic_max_qty > 0:
                playlist.playlist_line_ids[: -playlist.dynamic_max_qty].unlink()


class MusicPlaylistLine(models.Model):
    _name = "oomusic.playlist.line"
    _description = "Music Playlist Track"
    _order = "playlist_id, sequence"

    sequence = fields.Integer("Sequence", default=10)
    playlist_id = fields.Many2one(
        "oomusic.playlist", "Playlist", required=True, index=True, ondelete="cascade"
    )
    playing = fields.Boolean("Playing", default=False)
    track_id = fields.Many2one("oomusic.track", "Track", required=True, ondelete="cascade")
    track_number = fields.Char(
        "Track #", related="track_id.track_number", readonly=True, related_sudo=False
    )
    album_id = fields.Many2one(
        "oomusic.album", "Album", related="track_id.album_id", readonly=True, related_sudo=False
    )
    artist_id = fields.Many2one(
        "oomusic.artist", "Artist", related="track_id.artist_id", readonly=True, related_sudo=False
    )
    genre_id = fields.Many2one(
        "oomusic.genre", "Genre", related="track_id.genre_id", readonly=True, related_sudo=False
    )
    year = fields.Char("Year", related="track_id.year", readonly=True, related_sudo=False)
    duration = fields.Integer(
        "Duration", related="track_id.duration", readonly=True, related_sudo=False
    )
    duration_min = fields.Float(
        "Duration (min)", related="track_id.duration_min", readonly=True, related_sudo=False
    )
    user_id = fields.Many2one(
        "res.users", related="playlist_id.user_id", store=True, index=True, related_sudo=False
    )
    last_play = fields.Datetime("Last Played", readonly=True)

    def oomusic_set_current(self):
        now = fields.Datetime.now()
        res = {}
        if not self.id:
            return json.dumps(res)

        # Make sure all other playlists are not set as current
        if not self.playlist_id.current:
            self.playlist_id.action_current()

        # Update playing status and stats of the current playlist
        self.search([("playing", "=", True)]).playing = False
        self.last_play = now if self.playlist_id.dynamic else False
        self.playing = True

        # Specific case of a dynamic playlist
        self.playlist_id._update_dynamic()
        return json.dumps(res)

    def oomusic_play_skip(self, play=False):
        now = fields.Datetime.now()
        # Do not update the Play/Skip ratio more than once every 5 minutes for a given track
        if (
            self.track_id.last_play_skip_ratio
            and (now - self.track_id.last_play_skip_ratio).total_seconds() < 300
        ):
            return True
        if play:
            self.track_id.last_play = now
            self.track_id.play_count += 1
        else:
            self.track_id.last_skip = now
            self.track_id.skip_count += 1
        play_count = self.track_id.play_count or 1.0
        skip_count = self.track_id.skip_count or 1.0
        self.track_id.play_skip_ratio = play_count / skip_count
        self.track_id.last_play_skip_ratio = now
        return True

    def oomusic_play(self, seek=0):
        res = {}
        if not self:
            return json.dumps(res)

        ConfigParam = self.env["ir.config_parameter"].sudo()
        audio_mode = (
            "raw"
            if ConfigParam.get_param("oomusic.trans_disabled")
            else self.playlist_id.audio_mode
        )
        res["playlist_line_id"] = self.id
        res["audio"] = self.playlist_id.audio
        track_info = self.track_id._oomusic_info(seek=seek, mode=audio_mode)
        res.update(track_info)
        return json.dumps(res)

    def oomusic_previous(self, shuffle=False):
        res = {}
        # User might have removed the line from the playlist in the meantime => Fallback on first
        # track of playlist.
        try:
            lines = self.playlist_id.playlist_line_ids
        except MissingError:
            playlist = self.env["oomusic.playlist"].search([("current", "=", True)], limit=1)
            return playlist.playlist_line_ids[:1].oomusic_play()

        # Search for matching line, play first if end of list
        if shuffle:
            return self.oomusic_shuffle()
        try:
            idx = lines._ids.index(self._ids[0])
            if idx > 0:
                return lines[idx - 1].oomusic_play()
            else:
                return lines[len(lines) - 1].oomusic_play()
        except ValueError:
            pass
        return json.dumps(res)

    def oomusic_next(self, shuffle=False):
        res = {}
        # User might have removed the line from the playlist in the meantime => Fallback on first
        # track of playlist.
        try:
            lines = self.playlist_id.playlist_line_ids
        except MissingError:
            playlist = self.env["oomusic.playlist"].search([("current", "=", True)], limit=1)
            return playlist.playlist_line_ids[:1].oomusic_play()

        # Search for matching line, play last if beginning of list
        if shuffle:
            return self.oomusic_shuffle()
        try:
            idx = lines._ids.index(self._ids[0])
            if idx < (len(lines) - 1):
                return lines[idx + 1].oomusic_play()
            else:
                return lines[0].oomusic_play()
        except ValueError:
            pass
        return json.dumps(res)

    def oomusic_shuffle(self):
        lines = self.playlist_id.playlist_line_ids
        return lines[random.randint(0, len(lines) - 1)].oomusic_play()

    def oomusic_last_track(self):
        playlist = self.env["oomusic.playlist"].search([("current", "=", True)], limit=1)
        if not playlist:
            return json.dumps({})
        # Search for the playing track
        playlist_line = self.env["oomusic.playlist.line"].search(
            [("playlist_id", "=", playlist.id), ("playing", "=", True)], limit=1
        )
        if playlist_line:
            return playlist_line.oomusic_play()
        # Fallback on any track
        playlist_line = self.env["oomusic.playlist.line"].search(
            [("playlist_id", "=", playlist.id)], limit=1
        )
        if playlist_line:
            return playlist_line.oomusic_play()
        return json.dumps({})

    def action_play(self):
        return {
            "type": "ir.actions.act_play",
            "res_model": "oomusic.playlist.line",
            "res_id": self.id,
        }
