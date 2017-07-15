odoo.define('oomusic.Widget', function(require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var registry = require('web.field_registry');


/**
 * Displays a 'Play' button
 */
var PlayField = AbstractField.extend({
    className: 'oom_play fa fa-play',
    tagName: 'span',
    description: "",
    supportedFieldTypes: ['boolean'],
    events: {
        'click': '_onClick',
    },
    isSet: function () {
        return true;
    },
    _onClick: function (event) {
        event.preventDefault();
        event.stopPropagation();
        core.bus.trigger('oomusic_play', this.model, this.res_id);
    },
});

registry
    .add('oomusic_play', PlayField)
});
