/*
 * View model for OctoPrint-Cext
 *
 * Author: olemin
 * License: AGPLv3
 */
$(function() {
    function CextViewModel(parameters) {
      var self = this;
      self.settingsViewModel = parameters[0];
      self.printerProfilesViewModel = parameters[1];

      self.speed_probe_fast=ko.observable();
      self.speed_probe_fine=ko.observable();
      self.probe_offset_x=ko.observable();
      self.probe_offset_y=ko.observable();
      self.plate_coner_xy=ko.observable();
      self.z_travel=ko.observable();
      self.auto_next=ko.observable();
      self.auto_threshold=ko.observable();
      self.auto_count=ko.observable();
      self.z_probe_threshold=ko.observable();
      

      self.onBeforeBinding = function() {
        self.speed_probe_fast(self.settingsViewModel.settings.plugins.cExt.speed_probe_fast());
        self.speed_probe_fine(self.settingsViewModel.settings.plugins.cExt.speed_probe_fine());
        self.probe_offset_x(self.settingsViewModel.settings.plugins.cExt.probe_offset_x());
        self.probe_offset_y(self.settingsViewModel.settings.plugins.cExt.probe_offset_y());
        self.plate_coner_xy(self.settingsViewModel.settings.plugins.cExt.plate_coner_xy());
        self.z_travel(self.settingsViewModel.settings.plugins.cExt.z_travel());
        self.auto_next(self.settingsViewModel.settings.plugins.cExt.auto_next());
        self.auto_threshold(self.settingsViewModel.settings.plugins.cExt.auto_threshold());
        self.auto_count(self.settingsViewModel.settings.plugins.cExt.auto_count());
        self.auto_count(self.settingsViewModel.settings.plugins.cExt.auto_count());
      }

      self.onEventSettingsUpdated = function (payload) {
        self.speed_probe_fast(self.settingsViewModel.settings.plugins.cExt.speed_probe_fast());
        self.speed_probe_fine(self.settingsViewModel.settings.plugins.cExt.speed_probe_fine());
        self.probe_offset_x(self.settingsViewModel.settings.plugins.cExt.probe_offset_x());
        self.probe_offset_y(self.settingsViewModel.settings.plugins.cExt.probe_offset_y());
        self.plate_coner_xy(self.settingsViewModel.settings.plugins.cExt.plate_coner_xy());
        self.z_travel(self.settingsViewModel.settings.plugins.cExt.z_travel());
        self.auto_next(self.settingsViewModel.settings.plugins.cExt.auto_next());
        self.auto_threshold(self.settingsViewModel.settings.plugins.cExt.auto_threshold());
        self.auto_count(self.settingsViewModel.settings.plugins.cExt.auto_count());
        self.auto_count(self.settingsViewModel.settings.plugins.cExt.auto_count());
      }

    	self.onStartup = function() {
    		$('#control-jog-led').insertAfter('#control-jog-general');
    	}

          // assign the injected parameters, e.g.:
          // self.loginStateViewModel = parameters[0];
          // self.settingsViewModel = parameters[1];
      self.set_z_zero = function() { 
          OctoPrint.control.sendGcode("G92 Z0");// Set Position
      }
      
      self.z_hop = function() { 
        console.log(self.printerProfilesViewModel.currentProfileData());
        OctoPrint.control.sendGcode(["G91","G0 Z"+self.z_travel()+" F"+self.printerProfilesViewModel.currentProfileData().axes.z.speed()]);
      }

      self.level_begin = function(data) {
          $.ajax({
              url: API_BASEURL + "plugin/cExt",
              type: "POST",
              dataType: "json",
              data: JSON.stringify({
                  command: "level_begin"
              }),
              contentType: "application/json; charset=UTF-8"
          });
      };
      self.level_next = function(data) {
          $.ajax({
              url: API_BASEURL + "plugin/cExt",
              type: "POST",
              dataType: "json",
              data: JSON.stringify({
                  command: "level_next"
              }),
              contentType: "application/json; charset=UTF-8"
          });
      };
      self.probe = function(data) {
          $.ajax({
              url: API_BASEURL + "plugin/cExt",
              type: "POST",
              dataType: "json",
              data: JSON.stringify({
                  command: "probe",
                  distanse: self.z_travel()
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
        dependencies: [ "settingsViewModel", "printerProfilesViewModel" ],
        // Elements to bind to, e.g. #settings_plugin_cExt, #tab_plugin_cExt, ...
        elements: ["#side_bar_plugin_cExt","#settings_plugin_cExt_form"]
    });
});
