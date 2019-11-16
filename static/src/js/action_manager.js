odoo.define('oomusic.ActPlay', function (require) {
    "use strict";

    var core = require('web.core');
    var _t = core._t;

    /**
     * The purpose of this file is to add the support of Odoo actions of type
     * 'ir.actions.act_play' to the ActionManager.
     */

    var ActionManager = require('web.ActionManager');
    var core = require('web.core');

    ActionManager.include({
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Overrides to handle the 'ir.actions.act_play' actions.
         *
         * @override
         * @private
         */
        _handleAction: function (action, options) {
            if (action.type === 'ir.actions.act_play') {
                core.bus.trigger('oomusic_play', action.res_model, action.res_id);
                action.type = 'ir.actions.act_window_close';
            } else if (action.type === 'ir.actions.act_add') {
                this.do_notify(
                    action.res_model_name + _t(' added'),
                    action.res_model_name + ' "' + action.res_name + _t('" added to playlist.'),
                    false
                );
                action.type = 'ir.actions.act_window_close';
            }
            return this._super.apply(this, arguments);
        },

    });
});
