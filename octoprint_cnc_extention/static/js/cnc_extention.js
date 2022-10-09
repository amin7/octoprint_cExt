/*
 * View model for OctoPrint-cnc
 *
 * Author: olemin
 * License: AGPLv3
 */
$(function() {
    function cncExtenetionViewModel(parameters) {
      var self = this;
      self.tab_name="#tab_plugin_cnc_extention";
      self.settingsViewModel = parameters[0];
      self.printerProfilesViewModel = parameters[1];

      self.z_threshold=ko.observable();
      self.z_travel=ko.observable();  

      self.level_delta_z=ko.observable();
      self.probing_state=ko.observable();

      self.isOperational = ko.observable();
      self.file_name = ko.observable("");
      self.is_file_analysis = ko.observable(false);
      self.is_engrave_avaliable = ko.observable(false);

      self.log_scroll = ko.observable(true);

      self.file_selected_width=ko.observable();
      self.file_selected_depth=ko.observable();
      self.cmd_AbsolutePositioning="G90";
      self.cmd_RelativePositioning="G91";
      self.cmd_SetPositionX0Y0="G92 X0 Y0 Z0";
      self.cmd_SetPositionZ0="G92 Z0";
      self.cmd_DisableSteppers="M18"
      self.cmd_AdjustmentSteppers="M666"

      self.putLog=function(event){
        logs=$("#id_cnc_extention_log");
        pre=logs.val();
        if (pre !=""){
          pre+="\n"
        }
        logs.val(pre+event);
        if(self.log_scroll()){
          document.getElementById("id_cnc_extention_log").scrollTop = document.getElementById("id_cnc_extention_log").scrollHeight;
        }
      }
      
      self.log_scroll.subscribe(function(check) {
        if(check){
          document.getElementById("id_cnc_extention_log").scrollTop = document.getElementById("id_cnc_extention_log").scrollHeight;
        }
      });
      
      self.move_step_x=ko.observable();
      self.move_step_y=ko.observable();
      self.move_step_z=ko.observable();

      self.move_step_x.subscribe(function(val) {
        $("#cnc_extention_X_step_minus").html("X-"+val)
        $("#cnc_extention_X_step_plus").html("X+"+val)
      })
      self.move_step_y.subscribe(function(val) {
        $("#cnc_extention_Y_step_minus").html("Y-"+val)
        $("#cnc_extention_Y_step_plus").html("Y+"+val)
      })
      self.move_step_z.subscribe(function(val) {
        $("#cnc_extention_Z_step_minus").html("Z-"+val)
        $("#cnc_extention_Z_step_plus").html("Z+"+val)
      })
      self.move_step_x(10)
      self.move_step_y(10)
      self.move_step_z(10)

      self._upd_settings=function(){
        plugin_setting=self.settingsViewModel.settings.plugins.cnc_extention;
        self.z_threshold(plugin_setting.z_threshold());
        self.z_travel(plugin_setting.z_travel());
        self.level_delta_z(plugin_setting.level_delta_z());
      }

      self.set_move_step_xyz=function(val){
        self.move_step_x(val);
        self.move_step_y(val);
        self.move_step_z(val);
      }

      self.onBeforeBinding = function() {
        self._upd_settings();
      }

      self.onEventSettingsUpdated = function (payload) {
        self._upd_settings();
      }

    	self.onStartup = function() {
        //status send automaticaly when user logined in

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

      self._padSpaces=function (str,pad){
        len= str.length
        tt=""
        while(len<pad){
          len++;
          tt+=' '
        }
        return tt+str
      }

      self.onDataUpdaterPluginMessage = function(plugin, data) {
//        console.log(plugin);
        if (plugin != "cnc_extention") {
            return;
        }
        console.log(data);

        if((typeof data.CProbeControl)!='undefined'){
          upd=data.CProbeControl;
          if((typeof upd.state)!='undefined'){
            self.probing_state(upd.state);
            self.putLog(upd.state);
          }
        }

        if((typeof data.file_selected)!='undefined'){
          path="not_selected"
          if(data.file_selected){
            path=data.file_selected.path;
          }
          self.file_name(path)
          self.putLog("file:"+path);
        }

        if((typeof data.analysis)!='undefined'){
          if(data.analysis){
            upd=data.analysis;
            self.putLog("file analised: size("+upd.width.toFixed(2)+"x"+upd.depth.toFixed(2)+"), ofset("+upd.min.x.toFixed(2)+"x"+upd.min.y.toFixed(2)+"), z("+upd.min.z.toFixed(2)+","+upd.max.z.toFixed(2)+"))");
          }
        }

        if((typeof data.plane)!='undefined'){
          self.putLog("plane="+ JSON.stringify(data.plane));
          if(data.plane){
            self.file_selected_width(data.plane.width);
            self.file_selected_depth(data.plane.depth);
    
            self.is_file_analysis(true);
          }else{
            self.is_file_analysis(false);
          }
        }

        if((typeof data.is_engrave_ready)!='undefined'){
          self.is_engrave_avaliable(data.is_engrave_ready);
        }

        if((typeof data.CBedLevelControl)!='undefined' && data.CBedLevelControl){
          upd=data.CBedLevelControl;
          if (upd.state==="Init"){
            self.is_engrave_avaliable(false);
            self.putLog("probe_area state="+upd.state+",count="+upd.count);
          }else if (upd.state==="Progress"){
            self.putLog("probe_area state"+upd.state+" "+upd.step+"/"+upd.count);
          }else if (upd.state==="Done"){
            self.putLog("probe_area done");
          }else{
            self.putLog("probe_area state="+upd.state+", payload="+JSON.stringify(upd));
          }
        }
        
        if((typeof data.z_level_map)!='undefined' && data.z_level_map){//endrave progressing
          self.putLog('z_level_map');
          iRows=data.z_level_map.length;
          zHeighLog=""
          while(iRows){
            iRows--;
            zHeighLog+=self._padSpaces('<'+iRows+'>',5);
            data.z_level_map[iRows].forEach(function(item){
              zHeighLog+=self._padSpaces(item.toFixed(2),8);
            })
            zHeighLog+='\n'
          }
          zHeighLog+=self._padSpaces('',5);
          data.z_level_map[0].forEach(function(item,index){
              zHeighLog+=self._padSpaces('<'+index+'>',8);
            })
          self.putLog(zHeighLog);
        }

        if((typeof data.engrave_assist)!='undefined'){//endrave progressing
          self.putLog("engrave_assist="+data.engrave_assist);
        }

        if((typeof data.dry_run)!='undefined'){
          self.putLog("dry_run="+ JSON.stringify(data.dry_run));
        }

      };

      self.onTabChange = function(next, current) {
        //console.log(next,current);
        if(next === self.tab_name){
          self.send_single_cmd('tab_activate');
        } 
        if(current === self.tab_name){
          self.send_single_cmd('tab_deactivate');
        }     
      }
//---------------------------------------------------------
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


    self.probe_threshold = function(distanse,feed) {
      let _distanse=parseFloat(distanse);
      _distanse+=parseFloat(self.z_threshold());
      self.probe(_distanse,feed)
    }

    self._send_cmd=function(_data) {
      console.log("_send_cmd", _data);
      $.ajax({
          url: API_BASEURL + "plugin/cnc_extention",
          type: "POST",
          dataType: "json",
          data: JSON.stringify(_data),
          contentType: "application/json; charset=UTF-8"
      });
    };

    self.probe = function(_distanse,_feed) {
      //console.log(_distanse);
      self._send_cmd({command: "probe", distanse: parseFloat(_distanse), feed: parseFloat(_feed) });
    };
//-----------------------------------------------------------
    self.send_single_cmd=function(cmd) {
      self.putLog("<"+cmd+">");
      self._send_cmd({command: cmd})
    }

    self.probe_area = function() {
      // console.log("probe_area");
      self._send_cmd({
                command: "probe_area",
                feed_probe: self.settingsViewModel.settings.plugins.cnc_extention.speed_probe(),
                feed_z: self.printerProfilesViewModel.currentProfileData().axes.z.speed(),
                feed_xy: self.printerProfilesViewModel.currentProfileData().axes.x.speed(),
                level_delta_z: self.level_delta_z()
            });
    };

    self.steper_ajust=function(){
      self.putLog("<steper_ajust>");
      OctoPrint.control.sendGcode(self.cmd_AdjustmentSteppers+" Z"+$("#id_cnc_extention_steper_ajust").val())
    }

    self.refresh= function(){
      $("#id_cnc_extention_log").val("");
      self.send_single_cmd('status');
    }
  }//cncExtenetionViewModel

    OCTOPRINT_VIEWMODELS.push({
        construct: cncExtenetionViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ "settingsViewModel", "printerProfilesViewModel"],
        // Elements to bind to, e.g.n_cExt, ...
        elements: [/*"#settings_plugin_cnc_extention",*/"#tab_plugin_cnc_extention"]
    });
});
