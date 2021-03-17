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
      self.z_threshold=ko.observable();
      self.z_travel=ko.observable();  

      self.level_delta_z=ko.observable();
      self.z_tool_change=ko.observable();
      self.grid_area=ko.observable();
      self.probing_state=ko.observable();

      self.isOperational = ko.observable();
      self.swap_xy = ko.observable();
      self.swap_xy_is_set=false
      self.is_file_selected = ko.observable(false);
      self.is_file_analysis = ko.observable(false);
      self.is_engrave_avaliable = ko.observable(false);

      self.embed_url = ko.observable('');

      self.file_selected_width=0;
      self.file_selected_depth=0;
      self.cmd_AbsolutePositioning="G90";
      self.cmd_RelativePositioning="G91";
      self.cmd_SetPosition000="G92 X0 Y0 Z0";
      self.cmd_SetPositionZ0="G92 Z0";
      self.cmd_DisableSteppers="M18"
      
      self._upd_settings=function(){
        self.speed_probe_fast(self.settingsViewModel.settings.plugins.cExt.speed_probe_fast());
        self.speed_probe_fine(self.settingsViewModel.settings.plugins.cExt.speed_probe_fine());
        self.z_threshold(self.settingsViewModel.settings.plugins.cExt.z_threshold());
        self.z_travel(self.settingsViewModel.settings.plugins.cExt.z_travel());
        self.level_delta_z(self.settingsViewModel.settings.plugins.cExt.level_delta_z());
        self.z_tool_change(self.settingsViewModel.settings.plugins.cExt.z_tool_change());
        self.grid_area(self.settingsViewModel.settings.plugins.cExt.grid_area());
      }
      self.onBeforeBinding = function() {
        self._upd_settings();
      }

      self.onEventSettingsUpdated = function (payload) {
        self._upd_settings();
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

        if((typeof data.CProbeControl)!='undefined'){
          upd=data.CProbeControl;
          if((typeof upd.state)!='undefined'){
            self.probing_state(upd.state);
          }
        }

        if((typeof data.file_selected)!='undefined'){
          if(data.file_selected){
            upd=data.file_selected;
            $("#id_file_selected").text(upd.path)
            self.is_file_selected(true)
          }else{
            $("#id_file_selected").text(" ");
            self.is_file_selected(false)
          }
        }

        if((typeof data.analysis)!='undefined'){
          if(data.analysis){
            upd=data.analysis;
            self.file_selected_width = parseFloat(upd.width);
            self.file_selected_depth = parseFloat(upd.depth);
            
            $("#id_file_analisys").text(" size("+upd.width.toFixed(2)+"x"+upd.depth.toFixed(2)+"), ofset("+upd.min.x.toFixed(2)+"x"+upd.min.y.toFixed(2)+"), z("+upd.min.z.toFixed(2)+","+upd.max.z.toFixed(2)+")")
            self.is_file_analysis(true)
          }else{
            $("#id_file_analisys").text("");
            self.is_file_analysis(false)
          }
        }

        if((typeof data.CBedLevelControl)!='undefined'){
          upd=data.CBedLevelControl;
          let state=""

          if((typeof upd.state)!='undefined'){
            state+=upd.state
            self.is_engrave_avaliable(upd.state=="Done")
          }
          if((typeof upd.step)!='undefined'){
            state+=" "+ upd.step
          }
          if((typeof upd.count)!='undefined'){
            state+="/"+ upd.count
          }
          if(state){
            $("#id_cext_state").text(state);
          }
        }
        self.swap_xy_is_set=true
        if((typeof data.swap_xy)!='undefined'){
          self.swap_xy(data.swap_xy)
        }else{
          self.swap_xy(false)
        }
        self.swap_xy_is_set=false
      };

      self.onTabChange = function(next, current) {
        //console.log(next,current);
        if(next == '#tab_plugin_cExt'){
            self.embed_url(self.settingsViewModel.settings.webcam.streamUrl());
        } else {
            self.embed_url('');
        }
      }
//---------------------------------------------------------
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

      self.swap_xy.subscribe(function(is_swap) {
        if(!self.swap_xy_is_set){
           $.ajax({
              url: API_BASEURL + "plugin/cExt",
              type: "POST",
              dataType: "json",
              data: JSON.stringify({
                  command: "swap_xy",
                  active: is_swap
              }),
              contentType: "application/json; charset=UTF-8"
          });
        }
      });

      self.probe = function(_distanse,_feed) {
        //console.log(_distanse);
        $.ajax({
            url: API_BASEURL + "plugin/cExt",
            type: "POST",
            dataType: "json",
            data: JSON.stringify({
                command: "probe",
                distanse: parseFloat(_distanse),
                feed: parseFloat(_feed)
            }),
            contentType: "application/json; charset=UTF-8"
        });
      };

    self.probe_threshold = function(distanse,feed) {
      let _distanse=parseFloat(distanse);
      _distanse+=parseFloat(self.z_threshold());
      self.probe(_distanse,feed)
    }
//-----------------------------------------------------------
    self.send_single_cmd=function(cmd) {
      //  console.log((new Error().stack));
        $.ajax({
            url: API_BASEURL + "plugin/cExt",
            type: "POST",
            dataType: "json",
            data: JSON.stringify({
                command: cmd
            }),
            contentType: "application/json; charset=UTF-8"
        });
    };

    self.probe_area = function() {
     // console.log("probe_area");
        $.ajax({
            url: API_BASEURL + "plugin/cExt",
            type: "POST",
            dataType: "json",
            data: JSON.stringify({
                command: "probe_area",
                feed_probe: self.speed_probe_fast(),
                feed_z: self.printerProfilesViewModel.currentProfileData().axes.z.speed(),
                feed_xy: self.printerProfilesViewModel.currentProfileData().axes.x.speed(),
                grid: parseInt(self.grid_area()),
                level_delta_z: self.level_delta_z()
            }),
            contentType: "application/json; charset=UTF-8"
        });
    };

      //rounded to grid
    self.up_to_grid=function(val) {
      _val=parseFloat(val)
      if(_val===0){
        return 0
      }
      return Math.ceil(_val/self.grid_area())*self.grid_area();
      };  
    self.file_selected_width_grid=function() {
      return self.up_to_grid(self.file_selected_width);
      };  
    self.file_selected_depth_grid=function() {
      return self.up_to_grid(self.file_selected_depth);
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
        dependencies: [ "settingsViewModel", "printerProfilesViewModel"],
        // Elements to bind to, e.g. #settings_plugin_cExt, #tab_plugin_cExt, ...
        elements: ["#settings_plugin_cExt_form","#navbar_plugin_cExt","#tab_plugin_cExt"]
    });
});
