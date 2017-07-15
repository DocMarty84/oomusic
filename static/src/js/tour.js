odoo.define('oomusic.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('oomusic_tour', [{
    trigger: '.o_menu_entry_lvl_2[data-menu-xmlid="oomusic.menu_action_folder"], .oe_menu_leaf[data-menu-xmlid="oomusic.menu_action_folder"]',
    content: _t('Add your first music folder <b>here</b>'),
    position: 'bottom',
}, {
    trigger: ".o_list_button_add",
    content: _t("Let's create a new folder."),
    position: "right",
}, {
    trigger: ".o_field_widget.o_required_modifier",
    content: _t("Write the full path of your folder. Click on the 'Scan' button to add the content to your library!"),
    position: "top",
}]);

});
