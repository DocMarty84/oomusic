odoo.define('oomusic.TopButton', function(require) {
"use strict";

var core = require('web.core');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');


var TopButton = Widget.extend({
    template:'oomusic.TopButton',
    events: {
        "click": "_onClickToggleDisplay",
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickToggleDisplay: function (ev){
        ev.preventDefault();
        core.bus.trigger('oomusic_toggle_display');
    },
});

SystrayMenu.Items.push(TopButton);

return {
    TopButton: new TopButton(),
};

});
