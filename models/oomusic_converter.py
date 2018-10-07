# -*- coding: utf-8 -*-

import multiprocessing.dummy as mp
from multiprocessing import cpu_count
import os
import random
from shutil import copyfile, move
from tempfile import gettempdir
from time import sleep

from odoo import fields, models, api


class MusicConverter(models.Model):
    _name = 'oomusic.converter'
    _description = 'Music Converter'
    _order = 'name, id'

    def _default_transcoder_id(self):
        transcoder = self.env.ref('oomusic.oomusic_transcoder_0', raise_if_not_found=False)
        if transcoder:
            return transcoder.id
        return self.env['oomusic.transcoder'].search([], limit=1).id

    name = fields.Char('Name', required="1", default=fields.Date.today, copy=False)
    user_id = fields.Many2one(
        'res.users', string='User', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.user
    )
    comment = fields.Char('Comment')
    state = fields.Selection(
        [('draft', 'Draft'), ('running', 'Running'), ('done', 'Done'), ('cancel', 'Cancelled')],
        string='State', required=True, default='draft')
    transcoder_id = fields.Many2one(
        'oomusic.transcoder', string='Transcoder', required=True, readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda s: s._default_transcoder_id())
    bitrate = fields.Integer(
        'Bitrate/Quality', readonly=True, states={'draft': [('readonly', False)]}, default=0)
    dest_folder = fields.Char(
        'Destination Folder', readonly=True, states={'draft': [('readonly', False)]}, required=True,
        default=lambda s: os.path.join(gettempdir(), 'koozic', fields.Date.today()))
    max_threads = fields.Integer(
        'Max Threads', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        default=cpu_count())
    norm = fields.Boolean(
        'Normalize', default=False, readonly=True, states={'draft': [('readonly', False)]},
        help='Normalize playlist loudness thanks to the EBU R128 normalization. It requires '
             'FFmpeg >=3.2.1 which includes by default the appropriate library (libebur128).\n'
             'Transcoding will be significantly slower when activated.'
    )
    converter_line_ids = fields.One2many(
        'oomusic.converter.line', 'converter_id', string='Tracks', readonly=True, copy=True,
        states={'draft': [('readonly', False)]})
    album_id = fields.Many2one(
        'oomusic.album', string='Add Album Tracks', store=False,
        help='Encoding help. When selected, the associated album tracks are added for conversion.')
    artist_id = fields.Many2one(
        'oomusic.artist', string='Add Artist Tracks', store=False,
        help='Encoding help. When selected, the associated artist tracks are added for conversion.')
    playlist_id = fields.Many2one(
        'oomusic.playlist', string='Add Playlist Tracks', store=False,
        help='Encoding help. When selected, the associated playlist tracks are added for conversion.')
    progress = fields.Float('Progress', compute='_compute_progress')
    show_waiting = fields.Boolean('Show Waiting', compute='_compute_show_waiting')

    @api.depends('converter_line_ids.state')
    def _compute_progress(self):
        for cv in self:
            if cv.state == 'draft':
                cv.progress = 0.0
            elif cv.state == 'done':
                cv.progress = 100.0
            else:
                lines_done = cv.converter_line_ids.filtered(lambda r: r.state == 'done')
                cv.progress = float(len(lines_done))/float(len(cv.converter_line_ids)) * 100.0

    @api.depends('progress', 'state')
    def _compute_show_waiting(self):
        for cv in self:
            if cv.state == 'running' and not cv.progress:
                cv.show_waiting = True
            else:
                cv.show_waiting = False

    def _add_tracks(self, tracks, onchange=False):
        # Set starting sequence
        seq = self.converter_line_ids[-1:].sequence or 10

        converter_line = self.env['oomusic.converter.line']
        converter_tracks_ids = set(self.converter_line_ids.mapped('track_id').ids)
        for track in tracks:
            if track.id in converter_tracks_ids:
                continue
            converter_tracks_ids.add(track.id)
            seq = seq + 1
            data = {
                'sequence': seq,
                'track_id': track.id,
                'state': 'draft',
            }
            if onchange:
                # This will keep the line displayed in a (more or less) correct order while they
                # are added
                converter_line |= converter_line.new(data)
            else:
                data['converter_id'] = self.id
                converter_line.create(data)

        if onchange:
            self.converter_line_ids += converter_line

    @api.onchange('album_id')
    def _onchange_album_id(self):
        self._add_tracks(self.album_id.track_ids, onchange=True)
        self.album_id = False
        return {}

    @api.onchange('artist_id')
    def _onchange_artist_id(self, onchange=True):
        self._add_tracks(self.artist_id.track_ids, onchange=True)
        self.artist_id = False
        return {}

    @api.onchange('playlist_id')
    def _onchange_playlist_id(self, onchange=True):
        self._add_tracks(
            self.playlist_id.mapped('playlist_line_ids').mapped('track_id'), onchange=True)
        self.playlist_id = False
        return {}

    @api.onchange('transcoder_id')
    def _onchange_transcoder_id(self):
        self.bitrate = self.transcoder_id.bitrate

    @api.multi
    def action_purge(self):
        self.mapped('converter_line_ids').unlink()

    @api.multi
    def action_run(self):
        self.write({'state': 'running'})
        self.env.cr.execute('''
            UPDATE oomusic_converter_line SET state = 'waiting' WHERE converter_id IN %s
        ''', (tuple(self.ids),))

    @api.multi
    def action_draft(self):
        self.write({'state': 'draft'})
        self.env.cr.execute('''
            UPDATE oomusic_converter_line SET state = 'draft' WHERE converter_id IN %s
        ''', (tuple(self.ids),))

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})
        self.env.cr.execute('''
            UPDATE oomusic_converter_line
            SET state = 'cancel'
            WHERE converter_id IN %s AND state = 'waiting'
        ''', (tuple(self.ids),))

    @api.multi
    def action_convert(self):
        for cv in self:
            cv_pool = mp.Pool(processes=max(cv.max_threads or 1, 1))
            cv_lines = cv.converter_line_ids.filtered(lambda r: r.state == 'waiting')
            for i in range(len(cv_lines)):
                cv_pool.apply_async(cv_lines[i].convert)

            cv_pool.close()
            cv_pool.join()
            cv.write({'state': 'done'})

    @api.multi
    def cron_convert(self):
        self.search([('state', '=', 'running')]).action_convert()


class MusicConverterLine(models.Model):
    _name = 'oomusic.converter.line'
    _description = 'Music Converter Track'
    _order = 'sequence'

    sequence = fields.Integer('Sequence', default=10)
    converter_id = fields.Many2one(
        'oomusic.converter', 'Converter', required=True, ondelete='cascade')
    state = fields.Selection(
        [('draft', 'Draft'), ('waiting', 'Waiting'), ('done', 'Done'), ('cancel', 'Cancelled')],
        string='State', required=True, copy=False, default='draft')
    track_id = fields.Many2one('oomusic.track', 'Track', required=True, ondelete='cascade')
    track_number = fields.Char(
        'Track #', related='track_id.track_number', readonly=True, related_sudo=False)
    album_id = fields.Many2one(
        'oomusic.album', 'Album', related='track_id.album_id', readonly=True, related_sudo=False)
    artist_id = fields.Many2one(
        'oomusic.artist', 'Artist', related='track_id.artist_id', readonly=True, related_sudo=False)
    duration_min = fields.Float(
        'Duration (min)', related='track_id.duration_min', readonly=True, related_sudo=False)
    user_id = fields.Many2one(
        'res.users', related='converter_id.user_id', store=True, index=True, related_sudo=False)
    dummy_field = fields.Boolean('Dummy field')

    def convert(self):
        with api.Environment.manage():
            with self.pool.cursor() as cr:
                if not self.env.context.get('test_mode'):
                    new_self = self.with_env(self.env(cr))
                else:
                    new_self = self
                    sleep(random.random())
                # In case we manually canceled the job between line selection and conversion
                if new_self.state != 'waiting':
                    return
                transcoder = new_self.converter_id.transcoder_id

                # Prepare folder and file
                fn = new_self.track_id.path.replace(
                    new_self.track_id.root_folder_id.path, new_self.converter_id.dest_folder)
                fn_base, fn_ext = os.path.splitext(fn)
                try:
                    os.makedirs(os.path.dirname(fn))
                except OSError:
                    pass

                # Avoid upsampling, except for VBR and normalization
                if (
                        fn_ext[1:] == transcoder.output_format.name and
                        not new_self.converter_id.norm and
                        '-q:a' not in transcoder.command and (
                            not new_self.converter_id.bitrate or
                            new_self.converter_id.bitrate >= new_self.track_id.bitrate
                        )
                ):
                    copyfile(new_self.track_id.path, fn)
                else:
                    outdata = transcoder.transcode(
                        new_self.track_id.id, bitrate=new_self.converter_id.bitrate,
                        norm=new_self.converter_id.norm
                    ).stdout
                    fn_out = fn_base + '.' + transcoder.output_format.name
                    with open(fn_out + '.tmp', 'wb') as outfile:
                        for d in outdata:
                            outfile.write(d)
                    move(fn_out + '.tmp', fn_out)
                new_self.write({'state': 'done'})
