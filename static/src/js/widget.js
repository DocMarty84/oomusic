odoo.define('oomusic.Widget', function(require) {
"use strict";

var core = require('web.core');

var _t = core._t;
var QWeb = core.qweb;


var ColumnPlayField = core.list_widget_registry.get('field').extend({
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

var ColumnAddButton = core.list_widget_registry.get('button').extend({
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

core.list_widget_registry
    .add('field.oomusic_play', ColumnPlayField)
    .add('button.oomusic_add', ColumnAddButton)
});
