odoo.define('oomusic.JplayerControl', function(require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');

var QWeb = core.qweb;

var JplayerControl = core.Class.extend(core.mixins.PropertiesMixin, {
    init: function(parent, options) {
        var self = this;
        core.mixins.PropertiesMixin.init.call(this, parent);

        this.$player_selector = $(".jp-jplayer");
        this.$audio_selector = $(".jp-audio");
        this.player = this.$player_selector.jPlayer({
            supplied: "oga, mp3",
            volume: 1.0,
            wmode: "window",
            useStateClassSkin: true,
            autoBlur: false,
            keyEnabled: true,
    	});

        this.current_playlist_line_id = undefined;
        this.current_time = 0;
        this.current_progress = 0;
        this.repeat = true;
        this.shuffle = false;
        this.duration = 1;
        this.seek = 0;

        // Bus events
        core.bus.on('oomusic_play', this, this.play);

        // Built-in jPlayer events
        this.$player_selector.on($.jPlayer.event.ended, this, function (ev) {
            if (!self.repeat) {
                self.next(self.current_playlist_line_id);
            }
        });
        this.$player_selector.on($.jPlayer.event.repeat, this, function (ev) {
            self.repeat = !self.repeat;
        });
        this.$player_selector.on($.jPlayer.event.timeupdate, this, function (ev) {
            self._updateProgress(ev);
        });

        // Additional click events
        $('.jp-previous').on('click', this, function (ev) {
            self.previous(self.current_playlist_line_id);
        });
        $('.jp-next').on('click', this, function (ev) {
            self.next(self.current_playlist_line_id);
        });
        $('.jp-shuffle').on('click', this, function (ev) {
            self.shuffle = true;
            $('.jp-shuffle-off').closest('li').show();
            $('.jp-shuffle').closest('li').hide();
        });
        $('.jp-shuffle-off').on('click', this, function (ev) {
            self.shuffle = false;
            $('.jp-shuffle').closest('li').show();
            $('.jp-shuffle-off').closest('li').hide();
        });
        $('.jp-stop').on('click', this, function (ev) {
            self.seek = 0;
        });
        $('.o_progress').on('click', this, function (ev) {
            var seek = Math.round(
                self.duration * (ev.offsetX/$('.o_progress').width())
            );
            self.play_seek(seek);
        });
        $('.o_star').on('click', this, function (ev) {
            self.star(self.current_playlist_line_id);
        });

        // setInterval(this._updateProgress.bind(this), 1000);

        // Load last track played data
        this.last_track();
    },

    _updateProgress: function(ev) {
        // Update Progress Time
        var current_time = Math.round(ev.jPlayer.status.currentTime)
        if (current_time !== this.current_time) {
            this.current_time = current_time;
            var current_time_html = QWeb.render('oomusic.CurrentTime', {
                current_time: $.jPlayer.convertTime(this.seek + ev.jPlayer.status.currentTime),
            });
            $('.o_current_time').replaceWith(current_time_html);
        }

        // Update Progress Bar
        var current_progress = Math.round((
            (this.seek + ev.jPlayer.status.currentTime)/this.duration
        ) * 100);
        if (current_progress !== this.current_progress) {
            this.current_progress = current_progress;
            $('.o_progress_bar')
            .css('width', String(current_progress) + '%')
            .attr('aria-valuenow', current_progress);
        }
    },

    _play: function(data, play_now){
        var data_json = JSON.parse(data);
        this.current_playlist_line_id = data_json.playlist_line_id;
        this.$player_selector.jPlayer('setMedia', {
            'title': data_json.title,
            'oga': data_json.oga,
            'mp3': data_json.mp3,
        });
        if (play_now) {
            this.$player_selector.jPlayer('play');
        };
        var duration = QWeb.render('oomusic.Duration', {
            duration: $.jPlayer.convertTime(data_json.duration),
        });
        $('.o_duration').replaceWith(duration);
        var image = QWeb.render('oomusic.Albumart', {
            image: data_json.image,
        });
        $('.o_albumart').replaceWith(image);
        this.duration = data_json.duration;
    },

    play: function(model, record_id, view){
        if (!_.isNumber(record_id)) {
            return;
        }
        var self = this;
        this.seek = 0;
        new Model(model).call('jplayer_play', [[record_id]])
            .then(function (res) {
                if (view) {
                    view.reload();
                }
                self._play(res, true);
            }
        );
    },

    previous: function(playlist_line_id) {
        if (!_.isNumber(playlist_line_id)) {
            return;
        }
        var self = this;
        this.seek = 0;
        new Model('oomusic.playlist.line').call('jplayer_previous', [[playlist_line_id], this.shuffle])
            .then(function (res) {
                self._play(res, true);
            }
        );
    },

    next: function(playlist_line_id) {
        if (!_.isNumber(playlist_line_id)) {
            return;
        }
        var self = this;
        this.seek = 0;
        new Model('oomusic.playlist.line').call('jplayer_next', [[playlist_line_id], this.shuffle])
            .then(function (res) {
                self._play(res, true);
            }
        );
    },

    play_seek: function(seek){
        var self = this;
        var playlist_line_id = this.current_playlist_line_id;
        this.seek = seek;
        new Model('oomusic.playlist.line').call('jplayer_play', [[playlist_line_id], seek])
            .then(function (res) {
                self._play(res, true);
            }
        );
    },

    star: function(playlist_line_id) {
        if (!_.isNumber(playlist_line_id)) {
            return;
        }
        var self = this;
        new Model('oomusic.playlist.line').call('jplayer_star', [[playlist_line_id]]);
    },

    last_track: function(){
        var self = this;
        new Model('oomusic.playlist.line').call('jplayer_last_track', [[]])
            .then(function (res) {
                self._play(res, false);
            }
        );
    },

});

return {
    JplayerControl: JplayerControl,
};

});
