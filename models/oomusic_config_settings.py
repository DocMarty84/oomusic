# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.release import version


class MusicConfigSettings(models.TransientModel):
    _name = "oomusic.config.settings"
    _inherit = "res.config.settings"
    _description = "Music Settings"

    def _default_subsonic_format_id(self):
        if self.env.ref("oomusic.oomusic_format_mp3", False):
            return self.env.ref("oomusic.oomusic_format_mp3").id
        return 0

    def _default_trans_disabled(self):
        ConfigParam = self.env["ir.config_parameter"].sudo()
        return ConfigParam.get_param("oomusic.trans_disabled")

    cron = fields.Selection(
        [("active", "Active"), ("inactive", "Inactive")],
        string="Scheduled Actions",
        help="Activate automatic folder scan and image cache mechanism",
    )
    view = fields.Selection(
        [("kanban", "Kanban, with thumbnails"), ("tree", "List, without thumbnails")],
        string="Default Views",
    )
    ext_info = fields.Selection(
        [("auto", "Fetched automatically"), ("manual", "Fetched manually")],
        string="Artists and Events Info",
        default="auto",
        config_parameter="oomusic.ext_info",
    )
    folder_sharing = fields.Selection(
        [("inactive", "Inactive (user specific)"), ("active", "Active (shared amongst all users)")],
        string="Folder Sharing",
    )
    subsonic_format_id = fields.Many2one(
        "oomusic.format",
        string="Format",
        config_parameter="oomusic.subsonic_format_id",
        default=lambda s: s._default_subsonic_format_id(),
        help="Transcoding format for the Subsonic API. Change at your own risks!",
    )
    trans_disabled = fields.Boolean(
        "Disable Transcoding",
        config_parameter="oomusic.trans_disabled",
        default=lambda s: s._default_trans_disabled(),
        help="Disable transcoding everywhere. This option bypasses any other transcoding setting. "
        "Change at your own risks!",
    )
    version = fields.Char("Version", readonly=True)

    @api.model
    def get_values(self):
        res = super(MusicConfigSettings, self).get_values()
        cron = (
            self.env.ref("oomusic.oomusic_scan_folder")
            + self.env.ref("oomusic.oomusic_build_artists_image_cache")
            + self.env.ref("oomusic.oomusic_build_image_cache")
            + self.env.ref("oomusic.oomusic_build_lastfm_cache")
            + self.env.ref("oomusic.oomusic_build_spotify_cache")
        ).mapped("active")
        view = (
            self.env.ref("oomusic.action_album") + self.env.ref("oomusic.action_artist")
        ).mapped("view_mode")
        folder_sharing = (
            self.env.ref("oomusic.oomusic_album")
            + self.env.ref("oomusic.oomusic_artist")
            + self.env.ref("oomusic.oomusic_folder")
            + self.env.ref("oomusic.oomusic_genre")
            + self.env.ref("oomusic.oomusic_track")
        ).mapped("perm_read")
        res["cron"] = "active" if all([c for c in cron]) else "inactive"
        res["view"] = "tree" if all([v.split(",")[0] == "tree" for v in view]) else "kanban"
        res["folder_sharing"] = "inactive" if all([c for c in folder_sharing]) else "active"
        res["version"] = version
        return res

    def set_values(self):
        super(MusicConfigSettings, self).set_values()
        # Activate/deactive ir.cron
        (
            self.env.ref("oomusic.oomusic_scan_folder")
            + self.env.ref("oomusic.oomusic_build_artists_image_cache")
            + self.env.ref("oomusic.oomusic_build_image_cache")
            + self.env.ref("oomusic.oomusic_build_bandsintown_cache")
            + self.env.ref("oomusic.oomusic_build_lastfm_cache")
            + self.env.ref("oomusic.oomusic_build_spotify_cache")
        ).write({"active": bool(self.cron == "active")})
        # Set view order
        if self.view == "tree":
            view_mode_album = "tree,kanban,form,graph,pivot"
            view_mode_artist = "tree,kanban,form"
        else:
            view_mode_album = "kanban,tree,form,graph,pivot"
            view_mode_artist = "kanban,tree,form"
        self.env.ref("oomusic.action_album").write({"view_mode": view_mode_album})
        self.env.ref("oomusic.action_artist").write({"view_mode": view_mode_artist})
        # Set folder sharing
        (
            self.env.ref("oomusic.oomusic_album")
            + self.env.ref("oomusic.oomusic_artist")
            + self.env.ref("oomusic.oomusic_bandsintown_event")
            + self.env.ref("oomusic.oomusic_folder")
            + self.env.ref("oomusic.oomusic_genre")
            + self.env.ref("oomusic.oomusic_track")
        ).write({"perm_read": bool(self.folder_sharing == "inactive")})
        if self.folder_sharing == "inactive":
            self.env.cr.execute(
                """
                DELETE
                FROM oomusic_playlist_line
                WHERE id IN
                (
                    SELECT pl.id
                    FROM oomusic_playlist_line AS pl
                    JOIN oomusic_track AS t ON t.id = pl.track_id
                    WHERE t.user_id != pl.user_id
                )
            """
            )
            self.env.cr.execute(
                """
                DELETE
                FROM oomusic_preference
                WHERE user_id != res_user_id
            """
            )
        self.env["ir.config_parameter"].set_param(
            "oomusic.subsonic_format_name", self.subsonic_format_id.name
        )
