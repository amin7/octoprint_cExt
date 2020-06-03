/*
 * View model for OctoPrint-Cext
 *
 * Author: olemin
 * License: AGPLv3
 */
$(function() {
    function CextViewModel(parameters) {
        var self = this;

	self.onStartup = function() {
		$('#control-jog-led').insertAfter('#control-jog-general');
        $('#temperature-presets').insertAfter('#temperature-table');
	}

        // assign the injected parameters, e.g.:
        // self.loginStateViewModel = parameters[0];
        // self.settingsViewModel = parameters[1];

        // TODO: Implement your plugin's view model here.
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: CextViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ /* "loginStateViewModel", "settingsViewModel" */ ],
        // Elements to bind to, e.g. #settings_plugin_cExt, #tab_plugin_cExt, ...
        elements: [ /* ... */ ]
    });
});
