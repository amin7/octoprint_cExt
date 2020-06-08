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
        $('#temperature-presets').insertAfter('#temp');
	}

        // assign the injected parameters, e.g.:
        // self.loginStateViewModel = parameters[0];
        // self.settingsViewModel = parameters[1];
    self.funG114 = function() { 
        OctoPrint.control.sendGcode("M114").done(function (responce) {
        console.log(responce);
      });
    }

    self.level_begin = function(data) {
        $.ajax({
            url: API_BASEURL + "plugin/cExt",
            type: "POST",
            dataType: "json",
            data: JSON.stringify({
                command: "levelBegin"
            }),
            contentType: "application/json; charset=UTF-8"
        });
    };

  }//CextViewModel



    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.

           OctoPrint.control.sendGcode(CalGcode).done(function () {
      //OctoPrint.control.sendGcode(CalGcode.split("\n")).done(function () {
        console.log("   Gcode Sequence Sent");
      });

     */
    OCTOPRINT_VIEWMODELS.push({
        construct: CextViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ /* "loginStateViewModel", "settingsViewModel" */ ],
        // Elements to bind to, e.g. #settings_plugin_cExt, #tab_plugin_cExt, ...
        elements: ["#temperature-presets"]
    });
});
