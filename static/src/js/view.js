odoo.define('oomusic.View', function(require) {
"use strict";

var core = require('web.core');
var ListView = require('web.ListView');


ListView.List.include(/** @lends instance.web.ListView.List# */{
    init: function () {
        this._super.apply(this, arguments);

        // Listen on 'oomusic_reload' only in specific playlist views
        if (this.view.fields_view.arch.attrs.playlist) {
            core.bus.on('oomusic_reload', this, this.reloadFromPlay);
        }
    },

    row_clicked: function (e, view) {
        // Catch the click event on the list, so we can start playing the track
        if (this.view.fields_view.arch.attrs.playlist || $(e.target).hasClass('o_play')) {
            // Listen on the 'oomusic_reload' event since it was not loaded at init for tree view
            // inside form view.
            if ($(e.target).hasClass('o_play')) {
                core.bus.on('oomusic_reload', this, this.reloadFromPlay);
            }
            var model = this.dataset.model;
            var record_id = $(e.currentTarget).data('id');
            return core.bus.trigger('oomusic_play', model, record_id, this.view);
        }
        return this._super.apply(this, arguments);
    },

    reloadFromPlay: function (prev_id, curr_id, view) {
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
            // This is done because, when switching from one view to another, the 'destroy' method
            // is not called, so we cannot stop listening at that moment. So we must enforce
            // stopping listening to the bus event, otherwise we might reload views which are no
            // longer shown to the user.
            core.bus.off('oomusic_reload', this, this.reloadFromPlay);
        }
    },
});

});
