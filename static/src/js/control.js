odoo.define('oomusic.Control', function(require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');

var QWeb = core.qweb;


var Control = core.Class.extend(core.mixins.PropertiesMixin, {
    init: function(parent, options) {
        var self = this;
        core.mixins.PropertiesMixin.init.call(this, parent);

        this.sound = undefined;
        this.previous_playlist_line_id = undefined;
        this.current_playlist_line_id = undefined;
        this.repeat = false;
        this.shuffle = false;
        this.duration = 1;
        this.user_seek = 0;
        this.sound_seek = 0;

        // ========================================================================================
        // Bus events
        // ========================================================================================
        core.bus.on('oomusic_play', this, this.playWidget);

        // ========================================================================================
        // Click events
        // ========================================================================================
        // Progress bar
        $('.oom_progress').on('click', this, function (ev) {
            var user_seek = Math.round(
                self.duration * (ev.offsetX/$('.oom_progress').width())
            );
            self.playSeek(user_seek);
        });

        // Play button
        $('.oom_play').on('click', this, function (ev) {
            self.play(ev);
        });
        // Pause button
        $('.oom_pause').on('click', this, function (ev) {
            self.pause(ev);
        });
        // Stop button
        $('.oom_stop').on('click', this, function (ev) {
            self.stop();
        });
        // Previous button
        $('.oom_previous').on('click', this, function (ev) {
            self.previous(self.current_playlist_line_id);
        });
        // Next button
        $('.oom_next').on('click', this, function (ev) {
            self.next(self.current_playlist_line_id);
        });

        // Volume bar
        $('.oom_volume').on('input', this, function (ev) {
            Howler.volume(parseFloat($('.oom_volume').val())/100);
        });

        // Shuffle button
        $('.oom_shuffle').on('click', this, function (ev) {
            self.shuffle = true;
            $('.oom_shuffle_off').closest('li').show();
            $('.oom_shuffle').closest('li').hide();
        });
        // Shuffle off button
        $('.oom_shuffle_off').on('click', this, function (ev) {
            self.shuffle = false;
            $('.oom_shuffle').closest('li').show();
            $('.oom_shuffle_off').closest('li').hide();
        });
        // Repeat button
        $('.oom_repeat').on('click', this, function (ev) {
            self.repeat = true;
            $('.oom_repeat_off').closest('li').show();
            $('.oom_repeat').closest('li').hide();
        });
        // Repeat off button
        $('.oom_repeat_off').on('click', this, function (ev) {
            self.repeat = false;
            $('.oom_repeat').closest('li').show();
            $('.oom_repeat_off').closest('li').hide();
        });
        // Star button
        $('.oom_star').on('click', this, function (ev) {
            self.star(self.current_playlist_line_id);
        });

        // ========================================================================================
        // Infinite calls
        // ========================================================================================
        setInterval(this._updateProgress.bind(this), 1000);
        setInterval(this._checkEnded.bind(this), 1500);

        // Load last track played data
        this.lastTrack();
    },

    _convertTime: function(t) {
        t = (t && typeof t === 'number') ? t : 0;

        var minutes = '0' + Math.floor(t / 60);
        var seconds = '0' + (t - minutes * 60);
        return minutes.substr(-2) + ":" + seconds.substr(-2);
    },

    _updateProgress: function() {
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
        $('.oom_current_time').replaceWith(current_time_html);

        // Update Progress Bar every 1 %
        var current_progress = Math.round((
            (this.user_seek + this.sound.seek())/this.duration
        ) * 100);
        if (this.current_progress !== current_progress) {
            $('.oom_progress_bar')
                .css('width', String(current_progress) + '%')
                .attr('aria-valuenow', current_progress);
        }
        this.current_progress = current_progress;
    },

    _checkEnded: function() {
        if (!this.sound || !this.sound.playing() || this._checkEnded_locked === true) {
            return;
        }
        var self = this;

        // Check if we have reached the end of the track, since Howler won't fire a 'ended' event
        // in case of song being streamed.
        if (Math.ceil(this.user_seek + this.sound.seek()) - this.duration >= -0.5) {
            if (this.repeat) {
                this.playWidget('oomusic.playlist.line', this.current_playlist_line_id);
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
            setTimeout(function(){ self._checkEnded_locked = false; }, 5000);
        } else {
            this.sound_seek = sound_seek;
        }
    },

    _clearProgress: function() {
        this.user_seek = 0;
        var current_time_html = QWeb.render('oomusic.CurrentTime', {
            current_time: this._convertTime(0),
        });
        $('.oom_current_time').replaceWith(current_time_html);

        $('.oom_progress_bar')
            .css('width', String(0) + '%')
            .attr('aria-valuenow', 0);
    },

    _play: function(data, play_now, view){
        var self = this;
        var data_json = JSON.parse(data);
        this.previous_playlist_line_id = this.current_playlist_line_id;
        this.current_playlist_line_id = data_json.playlist_line_id;
        core.bus.trigger(
            'oomusic_reload', this.previous_playlist_line_id, this.current_playlist_line_id, view
        );

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
            $('.oom_pause').closest('li').show();
            $('.oom_play').closest('li').hide();
        } else {
            $('.oom_pause').closest('li').hide();
            $('.oom_play').closest('li').show();
        }

        // Update time, title and album picture
        this.duration = data_json.duration;
        var duration = QWeb.render('oomusic.Duration', {
            duration: this._convertTime(data_json.duration),
        });
        $('.oom_duration').replaceWith(duration);

        var title = QWeb.render('oomusic.Title', {
            title: data_json.title,
        });
        $('.oom_title').replaceWith(title);

        var image = QWeb.render('oomusic.Albumart', {
            image: data_json.image,
        });
        $('.oom_albumart').replaceWith(image);
    },

    playWidget: function(model, record_id, view){
        if (!_.isNumber(record_id)) {
            return;
        }
        var self = this;
        new Model(model).call('oomusic_play', [[record_id]])
            .then(function (res) {
                self.user_seek = 0;
                self._play(res, true, view);
            }
        );
    },

    playSeek: function(seek){
        if (!this.sound) {
            return;
        }
        var self = this;
        var playlist_line_id = this.current_playlist_line_id;
        new Model('oomusic.playlist.line').call('oomusic_play', [[playlist_line_id], seek])
            .then(function (res) {
                self.user_seek = seek;
                self._play(res, true);
            }
        );
    },

    play: function(ev){
        if (!this.sound) {
            return;
        }
        this.sound.play();
        $('.oom_pause').closest('li').show();
        $('.oom_play').closest('li').hide();
    },

    pause: function(ev){
        if (!this.sound) {
            return;
        }
        this.sound.pause();
        $('.oom_pause').closest('li').hide();
        $('.oom_play').closest('li').show();
    },

    stop: function(){
        if (this.sound) {
            this.sound.stop();
        }
        this._clearProgress();
        this.lastTrack();
    },

    previous: function(playlist_line_id) {
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

    next: function(playlist_line_id) {
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

    star: function(playlist_line_id) {
        if (!_.isNumber(playlist_line_id)) {
            return;
        }
        new Model('oomusic.playlist.line').call('oomusic_star', [[playlist_line_id]]);
    },

    lastTrack: function(){
        var self = this;
        new Model('oomusic.playlist.line').call('oomusic_last_track', [[]])
            .then(function (res) {
                self._play(res, false);
            }
        );
    },

});

return {
    Control: Control,
};

});
