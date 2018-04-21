odoo.define('oomusic.Panel', function (require) {
"use strict";

var core = require('web.core');
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
        this.cache_data = {};
        this.cache_sound = {};
        this.previous_playlist_line_id = undefined;
        this.next_playlist_line_id = undefined;
        this.current_playlist_line_id = undefined;
        this.current_track_id = undefined;
        this.current_model = 'oomusic.playlist.line';
        this.repeat = false;
        this.shuffle = false;
        this.duration = 1;
        this.user_seek = 0;
        this.sound_seek = 0;
        this.sound_seek_last_played = 0;

        // ========================================================================================
        // Bus events
        // ========================================================================================

        core.bus.on('oomusic_toggle_display', this, this._onBusToggleDisplay);
        core.bus.on('oomusic_play', this, this._onBusPlayWidget);

        // ========================================================================================
        // Infinite calls
        // ========================================================================================

        setInterval(this._infUpdateProgress.bind(this), 1000);
        setInterval(this._infCheckStuck.bind(this), 3000);
        setInterval(this._infLoadNext.bind(this), 5000);

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
            self._play(self.init_id, {play_now: false});
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

        return this._rpc({
                model: this.current_model,
                method: 'oomusic_play',
                args: [[id], seek],
            })
            .then(function (res) {
                self.user_seek = seek;
                self._play(res, {play_now: true, model: self.current_model});
            });
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

    stop: function (play_now, keep_loaded) {
        var self = this;
        if (this.sound && keep_loaded) {
            this.sound.stop();
        } else {
            this._clearCache();
        }
        this._clearProgress();
        this.lastTrack()
            .then(function(res) {
                self._play(res, {play_now: typeof(play_now) === 'boolean' ? play_now : false});
            }
        );

    },

    previous: function (playlist_line_id) {
        if (!_.isNumber(playlist_line_id)) {
            return;
        }
        var self = this;
        return this._rpc({
                model: 'oomusic.playlist.line',
                method: 'oomusic_previous',
                args: [[playlist_line_id], this.shuffle],
            })
            .then(function (res) {
                self.user_seek = 0;
                self._play(res, {play_now: true});
            });
    },

    next: function (playlist_line_id, params) {
        if (!_.isNumber(playlist_line_id)) {
            return;
        }
        var self = this;
        var params = _.extend(params || {}, {play_now: true});
        if (this.next_playlist_line_id) {
            self.user_seek = 0;
            self._play(this.cache_data[this.next_playlist_line_id], params);
            return $.when();
        } else {
            return this._rpc({
                    model: 'oomusic.playlist.line',
                    method: 'oomusic_next',
                    args: [[playlist_line_id], this.shuffle],
                })
                .then(function (res) {
                    self.user_seek = 0;
                    self._play(res, params);
                });
        }
    },

    star: function (track_id) {
        if (!_.isNumber(track_id)) {
            return;
        }
        return this._rpc({
                model: 'oomusic.track',
                method: 'oomusic_star',
                args: [[track_id]],
            })
    },

    lastTrack: function () {
        return this._rpc({
                model: 'oomusic.playlist.line',
                method: 'oomusic_last_track',
                args: [[]],
            })
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

    _play: function (data, params) {
        var self = this;
        var data_json = JSON.parse(data);
        var params = params || {};

        // Stop potential playing sound
        // We keep the sound in cache for Firefox when transcoding is activated. For some unknown
        // reason, this causes issues:
        // - in Chrome, the next sound fails to load properly in all cases
        // - in Firefox, seek() is never reset to zero
        if (this.sound) {
            if (/Firefox/.test(Howler._navigator.userAgent) && this.sound._src.match('raw=0')) {
                this.sound.stop();
            } else {
                this.sound.unload();
                this._clearCacheUnloaded();
            }
        }

        // Create Howler sound. We use the cache if the track comes from a playlist and the user has
        // not seeked. If the user has previewed a track of has seeked, we do not use the cache.
        if (data_json.src && (self.user_seek || !data_json.playlist_line_id)) {
            this.sound = self._newHowl(data_json)
        } else if (data_json.src) {
            if (!this.cache_sound[data_json.playlist_line_id]) {
                this.cache_sound[data_json.playlist_line_id] = self._newHowl(data_json)
            }
            this.sound = this.cache_sound[data_json.playlist_line_id];
        }

        if (params.play_now) {
            this.sound_seek_last_played = 0;
            this.sound.play();
            this.$el.find('.oom_pause').closest('li').show();
            this.$el.find('.oom_play').closest('li').hide();
        } else {
            this.$el.find('.oom_pause').closest('li').hide();
            this.$el.find('.oom_play').closest('li').show();
        }

        // Reset next sound
        this.next_playlist_line_id = undefined;

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

        // Update global data
        this._updateGlobalData(data, params);

    },

    _updateGlobalData: function (data, params) {
        var self = this;
        var data_json = JSON.parse(data);

        // Update global variables
        this.previous_playlist_line_id = this.current_playlist_line_id;
        if (data_json.playlist_line_id) {
            this.current_playlist_line_id = data_json.playlist_line_id;
        }
        this.current_track_id = data_json.track_id;
        this.current_model = params.model || 'oomusic.playlist.line'

        // Set current playling line and propagate to the views.
        if (this.current_model === 'oomusic.playlist.line') {
            return this._rpc({
                    model: 'oomusic.playlist.line',
                    method: 'oomusic_set_current',
                    args: [[this.current_playlist_line_id]],
                })
                .then(function () {
                    core.bus.trigger(
                        'oomusic_reload', self.previous_playlist_line_id,
                        self.current_playlist_line_id, params.view
                    );
                });
        }
    },

    _clearCache: function () {
        _.each(this.cache_sound, function (v, k) {
            v.unload()
        });
        this.cache_data = {};
        this.cache_sound = {};
    },

    _clearCacheUnloaded: function () {
        var self = this;
        _.each(this.cache_sound, function (v, k) {
            if (v && v._state === 'unloaded') {
                delete self.cache_sound[k];
            }
        });
        this.cache_data = {};
    },

    _newHowl: function (data_json) {
        var self = this;
        return new Howl({
            src: data_json.src,
            html5: true,
            onend: function () {
                self._onEnded();
            }
        });
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
        var current_progress = 100;
        if (this.duration !== 0) {
            var current_progress = Math.round((
                (this.user_seek + this.sound.seek())/this.duration
            ) * 100);
        }

        if (this.current_progress !== current_progress) {
            this.$el.find('.oom_progress_bar')
                .css('width', String(current_progress) + '%')
                .attr('aria-valuenow', current_progress);
        }
        this.current_progress = current_progress;
    },

    _infLoadNext: function () {
        var self = this;
        var skip = !this.sound || !this.sound.playing() || this.repeat || this.shuffle ||
                   Math.ceil(this.user_seek + this.sound.seek()) + 30.0 < this.duration;
        if (skip) {
            return;
        }
        return this._rpc({
                model: 'oomusic.playlist.line',
                method: 'oomusic_next',
                args: [[this.current_playlist_line_id], false],
            })
            .then(function (res) {
                var data_json = JSON.parse(res);
                self.next_playlist_line_id = data_json.playlist_line_id;
                self.cache_data[data_json.playlist_line_id] = res;
                if (data_json.src && !self.cache_sound[data_json.playlist_line_id]) {
                    self.cache_sound[data_json.playlist_line_id] = self._newHowl(data_json)
                }
            });
    },

    _infCheckStuck: function () {
        if (!this.sound || !this.sound.playing() || this._checkEnded_locked === true) {
            return;
        }
        var self = this;

        // Prevent being stuck because of some download error.
        var sound_seek = this.sound.seek();
        if (sound_seek !== 0.0) {
            this.sound_seek_last_played = sound_seek;
        }
        if (sound_seek === this.sound_seek) {
            console.log("Player seems stuck, trying to resume...");
            this._checkEnded_locked = true;
            this._clearCache();
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

    _onClickPrevious: _.debounce(function () {
        this.previous(this.current_playlist_line_id);
    }, 1000, true),

    _onClickNext: _.debounce(function () {
        this.next(this.current_playlist_line_id);
    }, 1000, true),

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

    _onEnded: function () {
        // It might happen that the song stops playing for no apparent reason, then switch to the
        // next one. Try to mitigate this by checking that it ended no more than 10 seconds before
        // the end.
        if (this.duration - this.user_seek - this.sound_seek_last_played > 10) {
            this._clearCache();
            this.playSeek(Math.floor(this.user_seek + this.sound_seek_last_played));
        } else if (this.repeat) {
            this.stop(true, true);
        } else {
            this.next(this.current_playlist_line_id);
        }
        return;
    },

    _onBusPlayWidget: function (model, record_id) {
        if (!_.isNumber(record_id)) {
            return;
        }
        var self = this;
        return this._rpc({
                model: model,
                method: 'oomusic_play',
                args: [[record_id]],
            })
            .then(function (res) {
                self.user_seek = 0;
                self._play(res, {play_now: true, model: model});
            });
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
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.Panel = new Panel(web_client);
        });
    },
});

});
