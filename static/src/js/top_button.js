odoo.define('oomusic.TopButton', function(require) {
"use strict";

var core = require('web.core');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');

var _t = core._t;
var QWeb = core.qweb;

var TopButton = Widget.extend({
    template:'oomusic.TopButton',
    events: {
        "click": "toggle_display",
    },
    toggle_display: function (ev){
        ev.preventDefault();
        core.bus.trigger('oomusic_toggle_display');
    },
});

SystrayMenu.Items.push(TopButton);

return {
    TopButton: TopButton,
};

});
