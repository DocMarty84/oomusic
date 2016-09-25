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
    row_clicked: function (e, view) {
        // Catch the click event on the field, so we can start playing the track
        if ($(e.target).hasClass('o_play')) {
            var model = this.dataset.model;
            var record_id = $(e.currentTarget).data('id');
            return core.bus.trigger('oomusic_play', model, record_id, this.view);
        }
        return this._super.apply(this, arguments);
    },
});

core.list_widget_registry
    .add('field.oomusic_play', ColumnOomusicPlayField)
    .add('button.oomusic_add', ColumnOomusicAddButton)
});
