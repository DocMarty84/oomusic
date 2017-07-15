odoo.define('oomusic.View', function(require) {
"use strict";

var core = require('web.core');
var ListView = require('web.ListView');
var ListRenderer = require('web.ListRenderer');
var ListController = require('web.ListController');


ListRenderer.include(/** @lends instance.web.ListView.List# */{
    init: function () {
        this._super.apply(this, arguments);

        // Listen on 'oomusic_reload' only in specific playlist views
        if (['playlist', 'playlist_form'].indexOf(this.arch.attrs.class) >= 0) {
            core.bus.on('oomusic_reload', this, this._reloadFromPlay);
        }
    },

    _onRowClicked: function (event) {
        // Catch the click event on the list, so we can start playing the track
        if (this.arch.attrs.class === 'playlist') {
            event.preventDefault();
            event.stopPropagation();

            var id = $(event.currentTarget).data('id');
            if (id) {
                this.trigger_up('oomusic_row_clicked_play', {id:id, target: event.target});
            }
            return;

        }
        return this._super.apply(this, arguments);
    },

    _renderHeaderCell: function (node) {
        if (node.attrs.widget === 'oomusic_play' || node.attrs.name === 'action_add_to_playlist') {
            return $('<th width=1></th>');
        }
        return this._super.apply(this, arguments);
    },

    _reloadFromPlay: function () {
        this.trigger_up('reload');
    },
});


ListController.include({
    custom_events: _.extend({}, ListController.prototype.custom_events, {
        oomusic_row_clicked_play: '_onRowClickedPlay',
    }),

    _onRowClickedPlay: function (event) {
        var record = this.model.get(event.data.id, {raw: true});
        core.bus.trigger('oomusic_play', record.model, record.res_id);
    },

});

});
