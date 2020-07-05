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
      self.isOperational = ko.observable();
      self.file_selected_path=ko.observable();
      self.file_selected_width=0;
      self.file_selected_depth=0;
      self.cmd_AbsolutePositioning="G90";
      self.cmd_RelativePositioning="G91";
      self.cmd_SetPosition000="G92 X0 Y0 Z0";
      self.cmd_SetPositionZ0="G92 Z0";
      self.cmd_DisableSteppers="M18"
      
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
    //		$('#control-jog-led').insertAfter('#control-jog-general');
    	}
      self.fromCurrentData = function (data) {
          self._processStateData(data.state);
      };

      self.fromHistoryData = function (data) {
          self._processStateData(data.state);
      };

      self._processStateData = function (data) {
       // console.log(data.flags);
        self.isOperational(data.flags.operational);
      };

      self.onDataUpdaterPluginMessage = function(plugin, data) {
        console.log(plugin);
        if (plugin != "cExt") {
            return;
        }
        console.log(data);

        if((typeof data.probe_state)!='undefined'){
           $("#id_probe_state").text(data.probe_state);
        }

        if((typeof data.file_selected_path)!='undefined'){
          self.file_selected_path(data.file_selected_path);
          }

        if((typeof data.file_selected_width)!='undefined' && (typeof data.file_selected_depth)!='undefined'){
          self.file_selected_width=data.file_selected_width;
          self.file_selected_depth=data.file_selected_depth;
          $("#id_file_selected_dimmention").text(self.file_selected_width.toFixed(1)+" x "+self.file_selected_depth.toFixed(1)+" mm");
        }else{
          $("#id_file_selected_dimmention").text("not available");
        }
      };

          // assign the injected parameters, e.g.:
          // self.loginStateViewModel = parameters[0];
          // self.settingsViewModel = parameters[1];
      self.relative_move_xy = function(offset_x,offset_y){
        let feed = self.printerProfilesViewModel.currentProfileData().axes.x.speed();
        OctoPrint.control.sendGcode([self.cmd_RelativePositioning,'G0 F'+feed+' X'+offset_x+' Y'+offset_y]);
      }

      self.absolute_move_xy = function(x,y){
        let feed = self.printerProfilesViewModel.currentProfileData().axes.x.speed();
        OctoPrint.control.sendGcode([self.cmd_AbsolutePositioning,'G0 F'+feed+' X'+x+' Y'+y]);
      }
      
      self.z_hop = function(distance) { 
    //    console.log(self.printerProfilesViewModel.currentProfileData());
        OctoPrint.control.sendGcode([self.cmd_RelativePositioning,"G0 Z"+distance+" F"+self.printerProfilesViewModel.currentProfileData().axes.z.speed()]);
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

      self.probe = function(_distanse,_feed) {
          $.ajax({
              url: API_BASEURL + "plugin/cExt",
              type: "POST",
              dataType: "json",
              data: JSON.stringify({
                  command: "probe",
                  distanse: _distanse,
                  feed: _feed
              }),
              contentType: "application/json; charset=UTF-8"
          });
      };
      
//-----------------------------------------------------------
    self.engrave=function() {
      };

    self.probe_area=function() {

      };
    self.probe_area_stop=function() {

      };
      //rounded to grid
    self.file_selected_width_grid=function() {
      return self.file_selected_width;
      };  
    self.file_selected_depth_grid=function() {
      return self.file_selected_depth;
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
        dependencies: [ "settingsViewModel", "printerProfilesViewModel" ,"controlViewModel"],
        // Elements to bind to, e.g. #settings_plugin_cExt, #tab_plugin_cExt, ...
        elements: ["#side_bar_plugin_cExt","#settings_plugin_cExt_form","#navbar_plugin_cExt","#tab_plugin_cExt"]
    });
});
