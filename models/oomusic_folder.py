# -*- coding: utf-8 -*-

import base64
import imghdr
import json
import logging
import os
from datetime import datetime as dt
from random import sample

from dateutil.relativedelta import relativedelta
from mutagen import File
from mutagen.flac import Picture
from psycopg2 import OperationalError

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MusicFolder(models.Model):
    _name = "oomusic.folder"
    _description = "Music Folder"
    _order = "path"

    name = fields.Char("Name")
    root = fields.Boolean("Top Level Folder", default=True)
    path = fields.Char("Folder Path", required=True, index=True)
    exclude_autoscan = fields.Boolean(
        "No auto-scan",
        default=False,
        help="Exclude this folder from the automatized scheduled scan. Useful if the folder is not "
        "always accessible, e.g. linked to an external drive.",
    )
    last_scan = fields.Datetime("Last Scanned")
    last_scan_duration = fields.Integer("Scan Duration (s)")
    last_commit = fields.Datetime("Last Commit")
    parent_id = fields.Many2one(
        "oomusic.folder", string="Parent Folder", index=True, ondelete="cascade"
    )
    child_ids = fields.One2many("oomusic.folder", "parent_id", string="Child Folders")
    user_id = fields.Many2one(
        "res.users",
        string="User",
        index=True,
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.user,
    )
    last_modification = fields.Integer("Last Modification")
    locked = fields.Boolean(
        "Locked",
        default=False,
        help='When a folder is being scanned, it is flagged as "locked". It might be necessary to '
        "unlock it manually if scanning has failed or has been interrupted.",
    )
    use_tags = fields.Boolean("Use ID3 Tags", default=True)
    tag_analysis = fields.Selection(
        [("taglib", "Taglib"), ("mutagen", "Mutagen")],
        "File Analysis",
        default="taglib",
        required=True,
        help="Choose Mutagen for better compatibility with remote mounting points, such as rclone.",
    )

    path_name = fields.Char("Folder Name", compute="_compute_path_name")
    track_ids = fields.One2many("oomusic.track", "folder_id", "Tracks")
    star = fields.Selection([("0", "Normal"), ("1", "I Like It!")], "Favorite", default="0")
    rating = fields.Selection(
        [("0", "0"), ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5")],
        "Rating",
        default="0",
    )
    root_preview = fields.Text("Preview Folder Content", compute="_compute_root_preview")
    root_total_artists = fields.Integer("Total Artists", compute="_compute_root_total")
    root_total_albums = fields.Integer("Total Albums", compute="_compute_root_total")
    root_total_tracks = fields.Integer("Total Tracks", compute="_compute_root_total")
    root_total_duration = fields.Integer("Total Duration", compute="_compute_root_total")
    root_total_size = fields.Integer("Total Size", compute="_compute_root_total")

    image_folder = fields.Binary(
        "Folder Image",
        compute="_compute_image_folder",
        help="This field holds the image used as image for the folder, limited to 1024x1024px.",
    )
    image_big = fields.Binary(
        "Big-sized Image",
        compute="_compute_image_big",
        inverse="_set_image_big",
        help="Image of the folder. It is automatically resized as a 1024x1024px image, with aspect "
        "ratio preserved.",
    )
    image_big_cache = fields.Binary(
        "Cache Of Big-sized Image",
        attachment=True,
        help="Image of the folder. It is automatically resized as a 1024x1024px image, with aspect "
        "ratio preserved.",
    )
    image_medium = fields.Binary(
        "Medium-sized Image",
        compute="_compute_image_medium",
        inverse="_set_image_medium",
        help="Image of the folder.",
    )
    image_medium_cache = fields.Binary(
        "Cache Of Medium-sized Image", attachment=True, help="Image of the folder"
    )
    image_small = fields.Binary(
        "Small-sized image",
        compute="_compute_image_small",
        inverse="_set_image_small",
        help="Image of the folder.",
    )
    image_small_cache = fields.Binary(
        "Cache Of Small-sized Image",
        attachment=True,
        help="Image of the folder, used in Kanban view",
    )

    _sql_constraints = [
        ("oomusic_folder_path_uniq", "unique(path, user_id)", "Folder path must be unique!")
    ]

    @api.depends("path")
    def _compute_path_name(self):
        for folder in self:
            if folder.root:
                folder.path_name = folder.path
            else:
                folder.path_name = folder.path.split(os.sep)[-1]

    @api.depends("path")
    def _compute_root_preview(self):
        ALLOWED_FILE_EXTENSIONS = self.env["oomusic.folder.scan"].ALLOWED_FILE_EXTENSIONS
        time_start = dt.now()
        for folder in self:
            if not folder.root or not folder.path:
                folder.root_preview = False
                continue
            i = 0
            fn_paths = ""
            for rootdir, dirnames, filenames in os.walk(folder.path):
                ii = 0
                for fn in filenames:
                    # Check file extension
                    fn_ext = fn.split(".")[-1]
                    if fn_ext and fn_ext.lower() not in ALLOWED_FILE_EXTENSIONS:
                        continue

                    fn_paths += "{}\n".format(os.path.join(rootdir.replace(folder.path, ""), fn))
                    i += 1
                    ii += 1
                    if ii > 3 or (dt.now() - time_start).total_seconds() > 2:
                        fn_paths += "...\n"
                        break
                if i > 30 or (dt.now() - time_start).total_seconds() > 2:
                    break
            if not fn_paths:
                fn_paths = _("No track found")
            folder.root_preview = fn_paths

    def _compute_root_total(self):
        folder_sharing = (
            "inactive" if self.env.ref("oomusic.oomusic_track").sudo().perm_read else "active"
        )
        for folder in self.filtered("root"):
            query_1 = [
                "SELECT COUNT(*) OVER()",
                "FROM oomusic_artist AS a",
                "JOIN oomusic_track AS t ON a.id = t.artist_id",
                "WHERE t.root_folder_id = {}".format(folder.id),
                "AND a.user_id = {}".format(self.env.user.id),
                "GROUP BY a.id",
            ]
            query_2 = [
                "SELECT COUNT(*) OVER()",
                "FROM oomusic_album AS a",
                "JOIN oomusic_track AS t ON a.id = t.album_id",
                "WHERE t.root_folder_id = {}".format(folder.id),
                "AND a.user_id = {}".format(self.env.user.id),
                "GROUP BY a.id",
            ]
            query_3 = [
                "SELECT COUNT(t.id), SUM(duration_min)/60.0, SUM(size)",
                "FROM oomusic_track AS t",
                "WHERE t.root_folder_id = {}".format(folder.id),
                "AND t.user_id = {}".format(self.env.user.id),
            ]
            if folder_sharing == "active":
                del query_1[4]
                del query_2[4]
                del query_3[3]
            self.env.cr.execute(" ".join(query_1))
            res_artists = self.env.cr.fetchall()
            self.env.cr.execute(" ".join(query_2))
            res_albums = self.env.cr.fetchall()
            self.env.cr.execute(" ".join(query_3))
            res_tracks = self.env.cr.fetchall()

            folder.root_total_artists = res_artists[0][0] if res_artists else 0
            folder.root_total_albums = res_albums[0][0] if res_albums else 0
            folder.root_total_tracks = res_tracks[0][0] if res_tracks else 0
            folder.root_total_duration = res_tracks[0][1] if res_tracks else 0
            folder.root_total_size = res_tracks[0][2] if res_tracks else 0

    def _compute_image_folder(self):
        accepted_names = ["folder", "cover", "front"]
        for folder in self:
            _logger.debug("Computing image folder %s...", folder.path)

            # Keep image files only
            files = [
                f
                for f in os.listdir(folder.path)
                if os.path.isfile(os.path.join(folder.path, f))
                and imghdr.what(os.path.join(folder.path, f))
            ]

            # Try to find an image with a name matching the accepted names
            folder.image_folder = False
            for f in files:
                for n in accepted_names:
                    if n in f.lower():
                        with open(os.path.join(folder.path, f), "rb") as img:
                            folder.image_folder = base64.b64encode(img.read())
                            break
                if folder.image_folder:
                    break
            if folder.image_folder:
                continue

            # Try to find an embedded cover art
            try:
                track = folder.track_ids[:1]
                track_ext = os.path.splitext(track.path)[1].lower() if track else ""
                song = File(track.path) if track else False
                if song:
                    data = False
                    if track_ext == ".mp3" and song.tags.getall("APIC"):
                        data = song.tags.getall("APIC")[0].data
                    elif track_ext == ".flac" and song.pictures:
                        data = song.pictures[0].data
                    elif track_ext in [".mp4", ".m4a"] and song.get("covr"):
                        data = song["covr"][0]
                    elif track_ext in [".oga", ".ogg", ".opus"] and song.get(
                        "metadata_block_picture"
                    ):
                        # The metadata block contains more than the picture. Indeed, it also
                        # contains other info related to the picture such as height, width,
                        # mimetype, etc. See for details:
                        # https://github.com/quodlibet/mutagen/blob/caaa2c5e31d/mutagen/flac.py#L604
                        #
                        # Therefore, we use the 'Picture' class which handles it.
                        b64_data = song["metadata_block_picture"][0]
                        data = Picture(base64.b64decode(b64_data)).data
                    if data:
                        folder.image_folder = base64.b64encode(data)
            except:
                _logger.debug(
                    "Error while getting embedded cover art of %s", track.path, exc_info=1
                )
                pass

    @api.depends("image_folder")
    def _compute_image_big(self):
        for folder in self:
            if folder.image_big_cache and not self.env.context.get("build_cache"):
                folder.image_big = folder.image_big_cache
                continue
            try:
                _logger.debug("Resizing image folder %s...", folder.path)
                resized_image = tools.image_process(
                    folder.image_folder, size=(1024, 1024), crop=True
                )
            except:
                _logger.warning(
                    "Error with image in folder '%s' (id: %s)",
                    folder.path,
                    folder.id,
                    exc_info=True,
                )
                continue

            folder.image_big = resized_image

            # Avoid useless save in cache
            if resized_image == folder.image_big_cache:
                continue

            # Save in cache
            try:
                folder.sudo().write({"image_big_cache": resized_image})
                self.env.cr.commit()
            except OperationalError:
                _logger.warning(
                    "Error when writing image cache for folder id: %s", folder.id, exc_info=True
                )

    @api.depends("image_folder")
    def _compute_image_medium(self):
        for folder in self:
            if folder.image_medium_cache and not self.env.context.get("build_cache"):
                folder.image_medium = folder.image_medium_cache
                continue
            try:
                _logger.debug("Resizing image folder %s...", folder.path)
                resized_image = tools.image_process(folder.image_folder, size=(128, 128), crop=True)
            except:
                _logger.warning(
                    "Error with image in folder '%s' (id: %s)",
                    folder.path,
                    folder.id,
                    exc_info=True,
                )
                continue

            folder.image_medium = resized_image

            # Avoid useless save in cache
            if resized_image == folder.image_medium_cache:
                continue

            # Save in cache
            try:
                folder.sudo().write({"image_medium_cache": resized_image})
                self.env.cr.commit()
            except OperationalError:
                _logger.warning(
                    "Error when writing image cache for folder id: %s", folder.id, exc_info=True
                )

    @api.depends("image_folder")
    def _compute_image_small(self):
        for folder in self:
            if folder.image_small_cache and not self.env.context.get("build_cache"):
                folder.image_small = folder.image_small_cache
                continue
            try:
                _logger.debug("Resizing image folder %s...", folder.path)
                resized_image = tools.image_process(folder.image_folder, size=(64, 64), crop=True)
            except:
                _logger.warning(
                    "Error with image in folder '%s' (id: %s)",
                    folder.path,
                    folder.id,
                    exc_info=True,
                )
                continue

            folder.image_small = resized_image

            # Avoid useless save in cache
            if resized_image == folder.image_small_cache:
                continue

            # Save in cache
            try:
                folder.sudo().write({"image_small_cache": resized_image})
                self.env.cr.commit()
            except OperationalError:
                _logger.warning(
                    "Error when writing image cache for folder id: %s", folder.id, exc_info=True
                )

    def _set_image_big(self):
        for folder in self:
            folder._set_image_value(folder.image_big)

    def _set_image_medium(self):
        for folder in self:
            folder._set_image_value(folder.image_medium)

    def _set_image_small(self):
        for folder in self:
            folder._set_image_value(folder.image_small)

    def _set_image_value(self, value):
        for folder in self:
            folder.image_folder = tools.image_process(value, size=(1024, 1024), crop=True)

    @api.model
    def create(self, vals):
        if "path" in vals and vals.get("root", True):
            vals["path"] = os.path.normpath(vals["path"])
        return super(MusicFolder, self).create(vals)

    def write(self, vals):
        if "path" in vals:
            vals["path"] = os.path.normpath(vals["path"])
            folders = self | self.search([("id", "child_of", self.ids)])
            folders.write({"last_modification": 0})
            tracks = self.env["oomusic.track"].search([("folder_id", "in", folders.ids)])
            tracks.write({"last_modification": 0})
        return super(MusicFolder, self).write(vals)

    def unlink(self):
        # Remove tracks and albums included in the folders.
        self.env["oomusic.track"].search([("folder_id", "child_of", self.ids)]).sudo().unlink()
        self.env["oomusic.album"].search([("folder_id", "child_of", self.ids)]).sudo().unlink()
        user_ids = self.mapped("user_id")
        super(MusicFolder, self).unlink()
        for user_id in user_ids:
            self.env["oomusic.folder.scan"]._clean_tags(user_id.id)

    def action_scan_folder(self):
        """
        This is the main method used to scan a oomusic folder. It creates a thread with the scanning
        process.
        """
        folder_id = self.id
        if folder_id:
            self.env["oomusic.folder.scan"].scan_folder_th(folder_id)

    def action_scan_folder_full(self):
        """
        This is a method used to force a full scan of a folder.
        """
        folder_id = self.id
        if folder_id:
            # Set the last modification date to zero so we force scanning all folders and files
            folders = self.env["oomusic.folder"].search([("id", "child_of", folder_id)]) | self
            folders.sudo().write({"last_modification": 0})
            tracks = self.env["oomusic.track"].search([("root_folder_id", "=", folder_id)])
            tracks.sudo().write({"last_modification": 0})
            self.env.cr.commit()
            self.env["oomusic.folder.scan"].scan_folder_th(folder_id)

    def action_unlock(self):
        return self.write({"locked": False})

    @api.model
    def cron_scan_folder(self):
        for folder in self.search([("root", "=", True), ("exclude_autoscan", "=", False)]):
            try:
                self.env["oomusic.folder.scan"]._scan_folder(folder.id)
            except:
                _logger.exception(
                    'Error while scanning folder "%s" (id: %s)',
                    folder.path,
                    folder.id,
                    exc_info=True,
                )

    @api.model
    def cron_build_image_cache(self):
        # Build a random sample of 500 folders to compute the images for. Every 50, the cache is
        # flushed.
        size_sample = 500
        size_step = 50
        folders = self.search([]).with_context(prefetch_fields=False)
        folders_sample = sample(folders.ids, min(size_sample, len(folders)))
        folders = self.browse(folders_sample).with_context(build_cache=True, prefetch_fields=False)
        for i in range(0, len(folders), size_step):
            folder = folders[i : i + size_step]
            folder._compute_image_big()
            folder._compute_image_medium()
            folder._compute_image_small()
            self.invalidate_cache()

    @api.model
    def cron_unlock_folder(self):
        domain = [
            ("root", "=", True),
            ("locked", "=", True),
            ("last_commit", "<", dt.now() - relativedelta(seconds=300)),
        ]
        folders = self.search(domain)
        if folders:
            _logger.warning(
                "The following folders seem locked for no reason: %s. Unlocking.", folders.ids
            )
            folders.action_unlock()

    def action_add_to_playlist(self):
        playlist = self.env["oomusic.playlist"].search([("current", "=", True)], limit=1)
        if not playlist:
            raise UserError(_("No current playlist found!"))
        if self.env.context.get("purge"):
            playlist.action_purge()
        lines = playlist._add_tracks(self.mapped("track_ids"))
        if self.env.context.get("play"):
            return {
                "type": "ir.actions.act_play",
                "res_model": "oomusic.playlist.line",
                "res_id": lines[:1].id,
            }

    def action_add_to_playlist_recursive(self):
        playlist = self.env["oomusic.playlist"].search([("current", "=", True)], limit=1)
        if not playlist:
            raise UserError(_("No current playlist found!"))
        if self.env.context.get("purge"):
            playlist.action_purge()
        tracks = self.env["oomusic.track"].search([("folder_id", "child_of", self.ids)])
        lines = playlist._add_tracks(tracks)
        if self.env.context.get("play"):
            return {
                "type": "ir.actions.act_play",
                "res_model": "oomusic.playlist.line",
                "res_id": lines[:1].id,
            }

    def oomusic_browse(self):
        res = {}
        if self.root or self.parent_id:
            res["parent_id"] = {"id": self.parent_id.id, "name": self.path_name or ""}
        if self:
            res["current_id"] = {"id": self.id, "name": self.path}
            res["child_ids"] = [{"id": c.id, "name": c.path_name} for c in self.child_ids]
        else:
            res["child_ids"] = [
                {"id": c.id, "name": c.path_name} for c in self.search([("root", "=", True)])
            ]
        res["track_ids"] = [
            {"id": t.id, "name": t.path.split(os.sep)[-1]}
            for t in self.track_ids.sorted(key="path")
        ]

        return json.dumps(res)
