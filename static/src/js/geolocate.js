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

        this.trigger_up('field_changed', {
            dataPointID: parent.state.id,
            changes: changes,
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
