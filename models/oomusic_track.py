# -*- coding: utf-8 -*-

from hashlib import sha1
import json
import os
from shutil import copyfile
from tempfile import gettempdir
from time import sleep
from urllib.parse import urlencode
from zipfile import ZipFile

from odoo import fields, models, _
from odoo.exceptions import UserError, MissingError


class MusicTrack(models.Model):
    _name = "oomusic.track"
    _description = "Music Track"
    _order = "album_id, disc, track_number_int, track_number, path"
    _inherit = ["oomusic.download.mixin", "oomusic.preference.mixin"]

    create_date = fields.Datetime(index=True)

    # ID3 Tags
    name = fields.Char("Title", required=True, index=True)
    artist_id = fields.Many2one("oomusic.artist", string="Artist", index=True)
    album_artist_id = fields.Many2one("oomusic.artist", string="Album Artist")
    album_id = fields.Many2one("oomusic.album", string="Album", index=True)
    disc = fields.Char("Disc")
    year = fields.Char("Year")
    track_number = fields.Char("Track #")
    track_number_int = fields.Integer("Track # (int)")
    track_total = fields.Char("Total Tracks")
    genre_id = fields.Many2one("oomusic.genre", string="Genre")
    description = fields.Char("Description")
    composer = fields.Char("Composer")
    performer_id = fields.Many2one("oomusic.artist", string="Original Artist")
    copyright = fields.Char("Copyright")
    contact = fields.Char("Contact")
    encoded_by = fields.Char("Encoder")

    # File data
    duration = fields.Integer("Duration", readonly=True)
    duration_min = fields.Float("Duration (min)", readonly=True)
    bitrate = fields.Integer("Bitrate (kbps)", readonly=True)
    path = fields.Char("Path", required=True, index=True, readonly=True)
    size = fields.Float("File Size (MiB)", readonly=True)
    play_count = fields.Integer(
        "Play Count",
        readonly=True,
        compute="_compute_play_count",
        inverse="_inverse_play_count",
        search="_search_play_count",
    )
    last_play = fields.Datetime(
        "Last Played",
        readonly=True,
        compute="_compute_last_play",
        inverse="_inverse_last_play",
        search="_search_last_play",
    )
    last_modification = fields.Integer("Last Modification", readonly=True)
    root_folder_id = fields.Many2one(
        "oomusic.folder", string="Root Folder", index=True, required=True
    )
    folder_id = fields.Many2one("oomusic.folder", string="Folder", index=True, required=True)

    user_id = fields.Many2one(
        "res.users",
        string="User",
        index=True,
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.user,
    )
    in_playlist = fields.Boolean("In Current Playlist", compute="_compute_in_playlist")
    star = fields.Selection(
        [("0", "Normal"), ("1", "I Like It!")],
        "Favorite",
        compute="_compute_star",
        inverse="_inverse_star",
        search="_search_star",
    )
    rating = fields.Selection(
        [("0", "0"), ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5")],
        "Rating",
        compute="_compute_rating",
        inverse="_inverse_rating",
        search="_search_rating",
    )
    tag_ids = fields.Many2many(
        "oomusic.tag",
        string="Custom Tags",
        compute="_compute_tag_ids",
        inverse="_inverse_tag_ids",
        search="_search_tag_ids",
    )

    def _compute_in_playlist(self):
        playlist = self.env["oomusic.playlist"].search([("current", "=", True)], limit=1)
        if not playlist:
            for track in self:
                track.in_playlist = False
            return
        query = """
            SELECT track_id
            FROM oomusic_playlist_line
            WHERE playlist_id = %s
        """
        self.env.cr.execute(query, (playlist.id,))
        track_ids_in_playlist = {r[0] for r in self.env.cr.fetchall() if r[0]}
        for track in self:
            track.in_playlist = False
        for track in self.env["oomusic.track"].browse(set(self.ids) & track_ids_in_playlist):
            track.in_playlist = True

    def _search_play_count(self, operator, value):
        res = super(MusicTrack, self)._search_play_count(operator, value)
        # Special case when we are searching for tracks never played. In this case, these tracks
        # might not have a corresponding record in oomusic.preference. So we need to manually add
        # the missing ids.
        if operator == "=" and value == 0:
            res = [("id", "in", res[0][2] + self._get_no_preference())]
        return res

    def _search_rating(self, operator, value):
        res = super(MusicTrack, self)._search_rating(operator, value)
        # Special case when we are searching for tracks with zero rating. In this case, these tracks
        # might not have a corresponding record in oomusic.preference. So we need to manually add
        # the missing ids.
        if operator == "=" and value == 0:
            res = [("id", "in", res[0][2] + self._get_no_preference())]
        return res

    def _get_no_preference(self):
        all_ids = set(self.search([]).ids)
        missing_ids = {
            t["res_id"]
            for t in self.env["oomusic.preference"]
            .search([("res_model", "=", "oomusic.track")])
            .read(["res_id"])
        }
        return list(all_ids - missing_ids)

    def _get_track_ids(self):
        return self

    def _build_zip(self, flatten=False, name=False):
        # Name is build using track ids, to avoid creating the same archive twice
        name = "-".join([str(id) for id in self.ids]) + ("-1" if flatten else "-0")
        name = sha1(name.encode("utf-8")).hexdigest()
        tmp_dir = gettempdir()
        z_name = os.path.join(tmp_dir, "{}.zip".format(name))

        # If file exists return it instead of creating a new archive
        if os.path.isfile(z_name):
            return z_name

        # Create the ZIP file
        seq = 1
        with ZipFile(z_name, "w") as z_file:
            base_arcname = "{:0%sd}-{}" % len(str(len(self)))
            for track in self:
                if flatten:
                    arcname = base_arcname.format(seq, os.path.split(track.path)[1])
                    path = os.path.join(tmp_dir, arcname)
                    copyfile(track.path, path)
                    z_file.write(path, arcname=arcname)
                    os.remove(path)
                    seq += 1
                else:
                    path = track.path
                    arcname = track.path.replace(track.root_folder_id.path, "")
                    z_file.write(path, arcname=arcname)
        sleep(0.2)
        return z_name

    def action_add_to_playlist(self):
        playlist = self.env["oomusic.playlist"].search([("current", "=", True)], limit=1)
        if not playlist:
            raise UserError(_("No current playlist found!"))
        if self.env.context.get("purge"):
            playlist.action_purge()
        playlist._add_tracks(self)

    def action_play(self):
        return {"type": "ir.actions.act_play", "res_model": "oomusic.track", "res_id": self.id}

    def oomusic_play(self, seek=0):
        if not self:
            return json.dumps({})
        ConfigParam = self.env["ir.config_parameter"].sudo()
        audio_mode = "raw" if ConfigParam.get_param("oomusic.trans_disabled") else "standard"
        return json.dumps(self._oomusic_info(seek=seek, mode=audio_mode))

    def oomusic_star(self):
        try:
            self.write({"star": "1"})
        except MissingError:
            return
        return

    def _oomusic_info(self, seek=0, mode="standard"):
        self.ensure_one()
        params = {"seek": seek, "mode": mode}
        raw_src = (
            [
                "/oomusic/trans/{}.{}?{}".format(
                    self.id, os.path.splitext(self.path)[1][1:], urlencode(params)
                )
            ]
            if mode == "raw"
            else []
        )

        # Even if the audio mode is raw, we still fall back on the regular transcoded modes
        params["mode"] = "standard" if mode == "raw" else mode
        return {
            "track_id": self.id,
            "title": (
                u"{} - {}".format(self.artist_id.name, self.name) if self.artist_id else self.name
            ),
            "duration": self.duration,
            "image": (
                (self.album_id.image_medium or self.artist_id.sp_image or b"").decode("utf-8")
                if not self.env.context.get("test_mode")
                else "TEST"
            ),
            "src": raw_src
            + [
                "/oomusic/trans/{}.{}?{}".format(self.id, ext, urlencode(params))
                for ext in self.env["oomusic.transcoder"]._get_browser_output_formats()
            ],
        }

    def _lastfm_track_getsimilar(self, count=50):
        self.ensure_one()
        url = (
            "https://ws.audioscrobbler.com/2.0/?method=track.getsimilar&artist="
            + self.artist_id.name
            + "&track="
            + self.name
            + "&limit="
            + str(count)
        )
        return json.loads(self.env["oomusic.lastfm"].get_query(url))
