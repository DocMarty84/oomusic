odoo.define('oomusic.Panel', function(require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var web_client = require('web.web_client');
var WebClient = require('web.WebClient');
var Widget = require('web.Widget');
var Control = require('oomusic.Control');

var player_panel = null;

var _t = core._t;
var QWeb = core.qweb;


var Panel = Widget.extend({
    template: "oomusic.Panel",
    events:{
    },

    init: function(parent) {
        if (player_panel) {
            return player_panel;
        }

        player_panel = this;
        this._super(parent);
        this.shown = false;
        this.appendTo(web_client.$el);
        this.oomusic_controls = new Control.Control();

        core.bus.on('oomusic_toggle_display', this, this.toggleDisplay);
    },

    start: function() {
        $('.oom_shuffle_off').closest('li').hide();
        $('.oom_repeat_off').closest('li').hide();
    },

    toggleDisplay: function(){
        if (this.shown) {
            this.$el.animate({
                "bottom": -this.$el.outerHeight(),
            });
        } else {
            this.$el.animate({
                "bottom": 0,
            });
        }
        this.shown = ! this.shown;
    },
});

WebClient.include({
    show_application: function(){
        return this._super.apply(this, arguments).then(function () {
            self.Panel = new Panel(web_client);
        });
    },
});

return {
    Panel: Panel,
};

});
