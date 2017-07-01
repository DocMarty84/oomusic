odoo.define('oomusic.Panel', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var web_client = require('web.web_client');
var WebClient = require('web.WebClient');
var Widget = require('web.Widget');

var player_panel = null;

var _t = core._t;
var QWeb = core.qweb;


var Panel = Widget.extend({
    template: "oomusic.Panel",
    events: {
        'click .oom_progress': '_onClickPlaySeek',      // Progress bar
        'click .oom_play': 'play',                    // Play button
        'click .oom_pause': 'pause',                  // Pause button
        'click .oom_stop': 'stop',                    // Stop button
        'click .oom_previous': '_onClickPrevious',      // Previous button
        'click .oom_next': '_onClickNext',              // Next button
        'click .oom_shuffle': '_onClickShuffle',        // Shuffle button
        'click .oom_shuffle_off': '_onClickShuffleOff', // Shuffle off button
        'click .oom_repeat': '_onClickRepeat',          // Repeat button
        'click .oom_repeat_off': '_onClickRepeatOff',   // Repeat off button
        'click .oom_star': '_onClickStar',              // Star button
        'input .oom_volume': '_onInputVolume',          // Volume bar
    },

    init: function (parent, options) {
        if (player_panel) {
            return player_panel;
        }
        player_panel = this;

        this._super.apply(this, arguments);

        this.shown = false;
        this.sound = undefined;
        this.previous_playlist_line_id = undefined;
        this.current_playlist_line_id = undefined;
        this.current_track_id = undefined;
        this.current_model = 'oomusic.playlist.line';
        this.repeat = false;
        this.shuffle = false;
        this.duration = 1;
        this.user_seek = 0;
        this.sound_seek = 0;

        // ========================================================================================
        // Bus events
        // ========================================================================================

        core.bus.on('oomusic_toggle_display', this, this._onBusToggleDisplay);
        core.bus.on('oomusic_play', this, this._onBusPlayWidget);

        // ========================================================================================
        // Infinite calls
        // ========================================================================================

        setInterval(this._infUpdateProgress.bind(this), 1000);
        setInterval(this._infCheckEnded.bind(this), 1500);

        this.appendTo(web_client.$el);

    },

    willStart: function () {
        var self = this;
        return this.lastTrack()
            .then(function (res) {
                self.init_id = res;
            }
        );
    },

    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function() {
            self.$el.find('.oom_shuffle_off').closest('li').hide();
            self.$el.find('.oom_repeat_off').closest('li').hide();
            self._play(self.init_id, false);
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    playSeek: function (seek) {
        if (!this.sound) {
            return;
        }
        var self = this;
        if (this.current_model === 'oomusic.track') {
            var id = this.current_track_id;
        } else {
            var id = this.current_playlist_line_id;
        }
        new Model(this.current_model).call('oomusic_play', [[id], seek])
            .then(function (res) {
                self.user_seek = seek;
                self._play(res, true, self.current_model);
            }
        );
    },

    play: function () {
        if (!this.sound) {
            return;
        }
        this.sound.play();
        this.$el.find('.oom_pause').closest('li').show();
        this.$el.find('.oom_play').closest('li').hide();
    },

    pause: function () {
        if (!this.sound) {
            return;
        }
        this.sound.pause();
        this.$el.find('.oom_pause').closest('li').hide();
        this.$el.find('.oom_play').closest('li').show();
    },

    stop: function (play_now) {
        var self = this;
        if (this.sound) {
            this.sound.stop();
        }
        this._clearProgress();
        this.lastTrack()
            .then(function(res) {
                self._play(res, typeof(play_now) === 'boolean' ? play_now : false);
            }
        );

    },

    previous: function (playlist_line_id) {
        if (!_.isNumber(playlist_line_id)) {
            return;
        }
        var self = this;
        new Model('oomusic.playlist.line').call('oomusic_previous', [[playlist_line_id], this.shuffle])
            .then(function (res) {
                self.user_seek = 0;
                self._play(res, true);
            }
        );
    },

    next: function (playlist_line_id) {
        if (!_.isNumber(playlist_line_id)) {
            return;
        }
        var self = this;
        new Model('oomusic.playlist.line').call('oomusic_next', [[playlist_line_id], this.shuffle])
            .then(function (res) {
                self.user_seek = 0;
                self._play(res, true);
            }
        );
    },

    star: function (track_id) {
        if (!_.isNumber(track_id)) {
            return;
        }
        new Model('oomusic.track').call('oomusic_star', [[track_id]]);
    },

    lastTrack: function () {
        return new Model('oomusic.playlist.line').call('oomusic_last_track', [[]]);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _convertTime: function (t) {
        t = (t && typeof t === 'number') ? t : 0;

        var minutes = '0' + Math.floor(t / 60);
        var seconds = '0' + (t - minutes * 60);
        return minutes.substr(-2) + ":" + seconds.substr(-2);
    },

    _clearProgress: function () {
        this.user_seek = 0;
        var current_time_html = QWeb.render('oomusic.CurrentTime', {
            current_time: this._convertTime(0),
        });
        this.$el.find('.oom_current_time').replaceWith(current_time_html);

        this.$el.find('.oom_progress_bar')
            .css('width', String(0) + '%')
            .attr('aria-valuenow', 0);
    },

    _play: function (data, play_now, model, view) {
        var self = this;
        var data_json = JSON.parse(data);
        this.previous_playlist_line_id = this.current_playlist_line_id;
        if (data_json.playlist_line_id) {
            this.current_playlist_line_id = data_json.playlist_line_id;
        }
        core.bus.trigger(
            'oomusic_reload', this.previous_playlist_line_id, this.current_playlist_line_id, view
        );
        this.current_track_id = data_json.track_id;
        this.current_model = model || 'oomusic.playlist.line'

        // Stop potential playing sound
        if (this.sound) {
            this.sound.unload();
        }

        // Create and play new sound
        this.sound = new Howl({
            src: [data_json.oga, data_json.mp3],
            html5: true,
        });
        if (play_now) {
            this.sound_seek_last_played = 0;
            this.sound.play();
            this.$el.find('.oom_pause').closest('li').show();
            this.$el.find('.oom_play').closest('li').hide();
        } else {
            this.$el.find('.oom_pause').closest('li').hide();
            this.$el.find('.oom_play').closest('li').show();
        }

        // Update time, title and album picture
        this.duration = data_json.duration;
        var duration = QWeb.render('oomusic.Duration', {
            duration: this._convertTime(data_json.duration),
        });
        this.$el.find('.oom_duration').replaceWith(duration);

        var title = QWeb.render('oomusic.Title', {
            title: data_json.title,
        });
        this.$el.find('.oom_title').replaceWith(title);

        var image = QWeb.render('oomusic.Albumart', {
            image: data_json.image,
        });
        this.$el.find('.oom_albumart').replaceWith(image);
    },

    _infUpdateProgress: function () {
        if (!this.sound || !this.sound.playing()) {
            return;
        }

        // Update Progress Time every second
        var current_time = Math.round(
            this.user_seek + this.sound.seek()
        );
        var current_time_html = QWeb.render('oomusic.CurrentTime', {
            current_time: this._convertTime(current_time),
        });
        this.$el.find('.oom_current_time').replaceWith(current_time_html);

        // Update Progress Bar every 1 %
        var current_progress = Math.round((
            (this.user_seek + this.sound.seek())/this.duration
        ) * 100);
        if (this.current_progress !== current_progress) {
            this.$el.find('.oom_progress_bar')
                .css('width', String(current_progress) + '%')
                .attr('aria-valuenow', current_progress);
        }
        this.current_progress = current_progress;
    },

    _infCheckEnded: function () {
        if (!this.sound || !this.sound.playing() || this._checkEnded_locked === true) {
            return;
        }
        var self = this;

        // Check if we have reached the end of the track, since Howler won't fire a 'ended' event
        // in case of song being streamed.
        if (Math.ceil(this.user_seek + this.sound.seek()) - this.duration >= -0.5) {
            if (this.repeat) {
                this.stop(true);
            } else {
                this.next(this.current_playlist_line_id);
            }
            return;
        }

        // Prevent being stuck because of some download error.
        var sound_seek = this.sound.seek();
        if (sound_seek !== 0.0) {
            this.sound_seek_last_played = sound_seek;
        }
        if (sound_seek === this.sound_seek) {
            console.log("Player seems stuck, trying to resume...");
            this._checkEnded_locked = true;
            this.playSeek(Math.floor(this.user_seek + this.sound_seek_last_played));
            setTimeout(function() { self._checkEnded_locked = false; }, 5000);
        } else {
            this.sound_seek = sound_seek;
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickPlaySeek: function (ev) {
        var user_seek = Math.round(
            this.duration * (ev.offsetX/this.$el.find('.oom_progress').width())
        );
        this.playSeek(user_seek);
    },

    _onClickPrevious: function () {
        this.previous(this.current_playlist_line_id);
    },

    _onClickNext: function () {
        this.next(this.current_playlist_line_id);
    },

    _onClickShuffle: function () {
        this.shuffle = true;
        this.$el.find('.oom_shuffle_off').closest('li').show();
        this.$el.find('.oom_shuffle').closest('li').hide();
    },

    _onClickShuffleOff: function () {
        this.shuffle = false;
        this.$el.find('.oom_shuffle').closest('li').show();
        this.$el.find('.oom_shuffle_off').closest('li').hide();
    },

    _onClickRepeat: function () {
        this.repeat = true;
        this.$el.find('.oom_repeat_off').closest('li').show();
        this.$el.find('.oom_repeat').closest('li').hide();
    },

    _onClickRepeatOff: function () {
        this.repeat = false;
        this.$el.find('.oom_repeat').closest('li').show();
        this.$el.find('.oom_repeat_off').closest('li').hide();
    },

    _onClickStar: function () {
        this.star(this.current_track_id);
    },

    _onInputVolume: function () {
        Howler.volume(parseFloat(this.$el.find('.oom_volume').val())/100);
    },

    _onBusPlayWidget: function (model, record_id, view) {
        if (!_.isNumber(record_id)) {
            return;
        }
        var self = this;
        new Model(model).call('oomusic_play', [[record_id]])
            .then(function (res) {
                self.user_seek = 0;
                self._play(res, true, model, view);
            }
        );
    },

    _onBusToggleDisplay: function () {
        if (this.shown) {
            this.$el.animate({
                "bottom": -this.$el.outerHeight(),
            });
        } else {
            this.$el.animate({
                "bottom": 0,
            });
        }
        this.shown = ! this.shown;
    },

});

WebClient.include({
    show_application: function () {
        return this._super.apply(this, arguments).then(function () {
            self.Panel = new Panel(web_client);
        });
    },
});

return {
    Panel: Panel,
};

});
