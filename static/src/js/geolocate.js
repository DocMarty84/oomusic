odoo.define('oomusic.geolocate', function (require) {
'use strict';

var widgetRegistry = require('web.widget_registry');
var Widget = require('web.Widget');

var Geolocate = Widget.extend({
    template: "oomusic.Geolocate",
    className: 'oomusic_geolocate',
    events: {
        'click': '_onClickButton',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _savePosition: function (position) {
        var changes = {};
        changes.latitude = position.coords.latitude;
        changes.longitude = position.coords.longitude;
        var parent = this.getParent();

        // The onSuccess function is a crappy workaround to make sure the value is not reset in the
        // interface bacause of the condition:
        //     event.target === this
        // in commit:
        // https://github.com/odoo/odoo/blob/8f4b98e67fe49516c0c830524de351db67c58357/addons/web/static/src/js/fields/basic_fields.js#L208
        // Indeed, 'event.target' is the widget, but 'this' is the latitude / longitude field.
        // Therefore, the condition is not met and the value is reset.
        var def = $.Deferred();
        this.trigger_up('field_changed', {
            dataPointID: parent.state.id,
            changes: changes,
            onSuccess: function () {
                parent.$('[name="latitude"]').val(changes.latitude);
                parent.$('[name="longitude"]').val(changes.longitude);
                def.resolve();
            },
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickButton: function (ev) {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(this.proxy('_savePosition'));
        }
    },



});

widgetRegistry.add('oomusic_geolocate', Geolocate);

return Geolocate;
});
