odoo.define('oomusic.View', function(require) {
"use strict";

var core = require('web.core');
var ListView = require('web.ListView');
var ListRenderer = require('web.ListRenderer');
var ListController = require('web.ListController');
var viewRegistry = require('web.view_registry');


//-----------------------------------------------------------------------------
// ListRenderer: behavior modification
//-----------------------------------------------------------------------------

ListRenderer.include(/** @lends instance.web.ListView.List# */{
    _renderHeaderCell: function (node) {
        if (node.attrs.name === 'action_play' || node.attrs.name === 'action_add_to_playlist') {
            return $(`<th data-name="${node.attrs.name}" width="1px"></th>`);
        }
        return this._super.apply(this, arguments);
    },
});


//-----------------------------------------------------------------------------
// PlaylistView
//-----------------------------------------------------------------------------

var PlaylistRenderer = ListRenderer.extend({
    init: function () {
        this._super.apply(this, arguments);
        core.bus.on('oomusic_reload', this, this._reloadFromPlay);
    },

    _onRowClicked: function (event) {
        // Catch the click event on the list, so we can start playing the track
        event.preventDefault();
        event.stopPropagation();

        var id = $(event.currentTarget).data('id');
        if (id) {
            this.trigger_up('oomusic_row_clicked_play', {id:id, target: event.target});
            return;
        }
        return this._super.apply(this, arguments);
    },

    _reloadFromPlay: function () {
        this.trigger_up('reload');
    },
});

var PlaylistController = ListController.extend({
    custom_events: _.extend({}, ListController.prototype.custom_events, {
        oomusic_row_clicked_play: '_onRowClickedPlay',
    }),

    _onRowClickedPlay: function (event) {
        var record = this.model.get(event.data.id, {raw: true});
        core.bus.trigger('oomusic_play', record.model, record.res_id);
    },
});

var PlaylistView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: PlaylistController,
        Renderer: PlaylistRenderer,
    }),
});

viewRegistry.add('playlist_tree', PlaylistView);

});
