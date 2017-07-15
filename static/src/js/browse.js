odoo.define('oomusic.Browse', function (require) {
'use strict';

var core = require('web.core');
var web_client = require('web.web_client');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;


var Browse = Widget.extend({
    events: {
        'click .oom_folder': '_onClickFolder',
        'click .fa-plus': '_onClickAddFolder',
        'click .oom_track': '_onClickAddTrack',
        'click .fa-play': '_onClickPreview',
    },

    init: function (parent, action) {
        this._super.apply(this, arguments);
        this.folder_id = action.context.folder_id || false;
        this.folder_data = action.context.folder_data || {}; // Used to cache requests
    },

    willStart: function () {
        return this.browse();
    },

    start: function () {
        // Render now, since events don't work when using the 'template' attribute.
        this.$el.html(QWeb.render('oomusic.Browse', {widget: this}));
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    browse: function () {
        var self = this;
        // Get folder data in the cache is available, otherwise request from the server
        if (this.folder_data[this.folder_id]) {
            return $.when();
        } else {
            return this._rpc({
                    model: 'oomusic.folder',
                    method: 'oomusic_browse',
                    args: [self.folder_id],
                })
                .then(function (data) {
                    var tmp_data = {};
                    tmp_data[self.folder_id] = JSON.parse(data);
                    _.extend(self.folder_data, tmp_data);
                });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickFolder: function (ev) {
        web_client.action_manager.do_action({
            type: 'ir.actions.client',
            tag: 'oomusic_browse',
            name: _t('Browse Files'),
            context: {
                folder_id: $(ev.target).data('id'),
                folder_data: this.folder_data,
            },
        });
    },

    _onClickAddFolder: function (ev) {
        ev.stopPropagation();
        var self = this;
        return this._rpc({
                model: 'oomusic.folder',
                method: 'action_add_to_playlist',
                args: [$(ev.target).parent().data('id')],
            })
            .then(function () {
                self.do_notify(
                    _t('Folder added'),
                    _t('Folder "') + $(ev.target).parent().text().trim() + _t('" added to playlist.'),
                    false
                );
            });
    },

    _onClickAddTrack: function (ev) {
        var self = this;
        return this._rpc({
                model: 'oomusic.track',
                method: 'action_add_to_playlist',
                args: [$(ev.target).data('id')],
            })
            .then(function () {
                self.do_notify(
                    _t('Track added'),
                    _t('Track "') + $(ev.target).text().trim() + _t('" added to playlist.'),
                    false
                );
            });
    },

    _onClickPreview: function (ev) {
        ev.stopPropagation();
        return core.bus.trigger('oomusic_play', 'oomusic.track', $(ev.target).parent().data('id'));
    },
});

core.action_registry.add('oomusic_browse', Browse);
return {
    Browse: Browse,
};
});
