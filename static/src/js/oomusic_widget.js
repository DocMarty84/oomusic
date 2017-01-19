odoo.define('oomusic.OomusicWidget', function(require) {
"use strict";

var core = require('web.core');
var ListView = require('web.ListView');

var _t = core._t;
var QWeb = core.qweb;


var ColumnOomusicPlayField = core.list_widget_registry.get('field').extend({
    /**
     * Return a 'Play' button. It should be linked to a dummy field.
     */
    heading: function () {
        return '<span class="o_play fa fa-play invisible"></span>';
    },
    width: function () {
        return 1;
    },
    _format: function (row_data, options) {
        return '<span class="o_play fa fa-play" title="' + _t('Play') + '"/>';
    },
});

var ColumnOomusicAddButton = core.list_widget_registry.get('button').extend({
    /**
     * Return a 'Add' button, with a narrow column
     */
    heading: function () {
        return '<span class="fa fa-plus invisible"></span>';
    },
    width: function () {
        return 1;
    },
});

ListView.List.include(/** @lends instance.web.ListView.List# */{
    init: function() {
        this._super.apply(this, arguments);

        // Listen on 'oomusic_reload' only in specific playlist views
        if (this.view.fields_view.arch.attrs.playlist) {
            core.bus.on('oomusic_reload', this, this.reload_from_play);
        }
    },
    row_clicked: function (e, view) {
        // Catch the click event on the list, so we can start playing the track
        if (this.view.fields_view.arch.attrs.playlist || $(e.target).hasClass('o_play')) {
            // Listen on the 'oomusic_reload' event since it was not loaded at init for tree view
            // inside form view.
            if ($(e.target).hasClass('o_play')) {
                core.bus.on('oomusic_reload', this, this.reload_from_play);
            }
            var model = this.dataset.model;
            var record_id = $(e.currentTarget).data('id');
            return core.bus.trigger('oomusic_play', model, record_id, this.view);
        }
        return this._super.apply(this, arguments);
    },
    reload_from_play: function (prev_id, curr_id, view) {
        // - view is a view on which the user has clicked. It can be a list view inside a form view.
        // - active_view is the active view in the action manager, in case the reload was triggered
        //   from the player.
        var active_view = this.view.getParent() && this.view.getParent().active_view.controller;
        if (view || (active_view && active_view.fields_view.arch.attrs.playlist)) {
            prev_id && this.records.get(prev_id) && this.reload_record(this.records.get(prev_id));
            curr_id && this.records.get(curr_id) && this.reload_record(this.records.get(curr_id));
        }
        if (!(active_view && active_view.fields_view.arch.attrs.playlist)) {
            // Stop listening if the view is not the playlist view
            core.bus.off('oomusic_reload', this, this.reload_from_play);
        }
    }
});

core.list_widget_registry
    .add('field.oomusic_play', ColumnOomusicPlayField)
    .add('button.oomusic_add', ColumnOomusicAddButton)
});
