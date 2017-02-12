odoo.define('oomusic.Browse', function (require) {
'use strict';

var core = require('web.core');
var Model = require('web.Model');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;


var Browse = Widget.extend({
    events: {
        'click .oom_folder': 'openFolder',
        'click .fa-plus': 'addFolder',
        'click .oom_track': 'addTrack',
    },

    init: function (parent, action) {
        this._super.apply(this, arguments);
        this.folder_id = action.context.folder_id || false;
        this.folder_data = action.context.folder_data || {}; // Used to cache requests
    },

    willStart: function () {
        return this.browse();
    },

    start: function() {
        // Render now, since events don't work when using the 'template' attribute.
        this.$el.html(QWeb.render('oomusic.Browse', {widget: this}));
        return this._super.apply(this, arguments);
    },

    browse: function () {
        var self = this;
        // Get folder data in the cache is available, otherwise request from the server
        if (this.folder_data[this.folder_id]) {
            return $.when();
        } else {
            return new Model('oomusic.folder').call('oomusic_browse', [self.folder_id]).then(function (data) {
                var tmp_data = {};
                tmp_data[self.folder_id] = JSON.parse(data);
                _.extend(self.folder_data, tmp_data);
            });
        }
    },

    openFolder: function (ev) {
        this.do_action({
            type: 'ir.actions.client',
            tag: 'oomusic_browse',
            name: _t('Browse Files'),
            context: {
                folder_id: $(ev.target).data('id'),
                folder_data: this.folder_data,
            },
        });
    },

    addFolder: function (ev) {
        ev.stopPropagation();
        var self = this;
        new Model('oomusic.folder')
            .call('action_add_to_playlist', [$(ev.target).parent().data('id')])
            .then(function () {
                self.do_notify(
                    _t('Folder added'),
                    _t('Folder "') + $(ev.target).parent().text().trim() + _t('" added to playlist.'),
                    false
                );
            });
    },

    addTrack: function (ev) {
        var self = this;
        new Model('oomusic.track')
            .call('action_add_to_playlist', [$(ev.target).data('id')])
            .then(function () {
                self.do_notify(
                    _t('Track added'),
                    _t('Track "') + $(ev.target).text().trim() + _t('" added to playlist.'),
                    false
                );
            });
    },
});

core.action_registry.add('oomusic_browse', Browse);
return {
    Browse: Browse,
};
});
