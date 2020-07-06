# coding=utf-8
from __future__ import absolute_import

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.
import octoprint.plugin
import re

from collections import deque
class CCmdList:
	def __init__(self, sendGCode):
		self.sendGCode = sendGCode

	class CCommand:
		def __init__(self, command, callBack =None):
			self.command = command
			self.callBack = callBack

	cmdList=deque()
	processingCommand=None
	response=[]

	def clearCommandList(self):
		self.cmdList.clear()

	def processCommandList(self):
		if self.processingCommand==None:
			if self.cmdList:
				self.processingCommand=self.cmdList.popleft()
				self.sendGCode(self.processingCommand.command)	
				#self._printer.commands(
				#send cmd


	def addGCode(self,commands,callBack = None):
		if isinstance(commands, list):  
			commlen=len(commands)
			for i in range(commlen):
				cmd=self.CCommand(commands[i]);
				if(i==commlen-1):
					cmd.callBack=callBack
				self.cmdList.append(cmd)
			pass
		else:
			self.cmdList.append(self.CCommand(commands,callBack))
			pass
		self.processCommandList()

	def processResponce(self,response):
		if self.processingCommand!=None:
			if not response.startswith("echo:busy: processing"):
				self.response.append(response);
				if(response.startswith('ok')):
					if(self.processingCommand.callBack!=None):
						self.processingCommand.callBack(self.response)
					self.processingCommand=None
					self.response=[]
					self.processCommandList()

GCODE_ABSOLUTE_POSITIONING ='G90'
GCODE_RELATIVEPOSITIONING ='G91'
GCODE_PROBE_UP="G38.4 F{feed} Z{dist}"
GCODE_PROBE_DOWN="G38.2 F{feed} Z{dist}"
GCODE_AUTO_HOME="G28 {axis}"
GCODE_MOVE_XY="G0 F{feed} X{pos_x} Y{pos_y}"
GCODE_MOVE_Z="G0 F{feed} Z{dist}"

class CextPlugin(octoprint.plugin.SettingsPlugin,
                 octoprint.plugin.AssetPlugin,
                 octoprint.plugin.TemplatePlugin,
                 octoprint.plugin.SimpleApiPlugin,
                 octoprint.plugin.StartupPlugin,
                 octoprint.plugin.EventHandlerPlugin):

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			speed_probe_fast=40,
			speed_probe_fine=20,
			z_threshold=1,
			z_travel=10,
			level_delta_z=1,
			z_tool_change=20,
			grid_area=10
		)

	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/cExt.js"],
			css=["css/cExt.css"],
			less=["less/cExt.less"]
		)

	#~~ TemplatePlugin mixin

	def get_template_configs(self):
		return [
			dict(type="sidebar", icon="arrows-alt"),
			dict(type="settings")
		]

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
		# for details.
		return dict(
			cExt=dict(
				displayName="Cext Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="you",
				repo="octoprint_cExt",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/you/octoprint_cExt/archive/{target_version}.zip"
			)
		)

	cmdList=None
	printer_cfg=None
	file_selected_path=""
	file_selected_origin=None


	def on_after_startup(self):
		self.cmdList = CCmdList(self._printer.commands)
		self.printer_cfg=self._printer_profile_manager.get_current()
		self._logger.info("PluginA starting up")
		self._logger.info(self._printer_profile_manager.get_current())
		self._logger.info(self._settings)
		pass

	def on_event(self, event, payload):
		self._logger.info(event)
		self._logger.info(payload)
		if(event=='FileSelected'):
			self.file_selected_path=payload['path']
			self.file_selected_origin=payload['origin']
			self._update_front()
			return
		if(event=='UserLoggedIn'):
			self._update_front()
			return
		pass

	def _update_front(self):
		data=dict()
		data['file_selected_path']=self.file_selected_path
		if self._file_manager.has_analysis(self.file_selected_origin,self.file_selected_path):
			analysis=self._file_manager.get_metadata(self.file_selected_origin,self.file_selected_path)['analysis']
			self._logger.info(analysis)
			data['file_selected_width']=analysis['dimensions']['width']
			data['file_selected_depth']=analysis['dimensions']['depth']
		self._plugin_manager.send_plugin_message(self._identifier, data)

	
#----------------------------------
# bed level
	# levelPos=None

	# def level_next(self):
	# 	if(self.levelPos==None):
	# 		return
	# 	dx=self.printer_cfg['volume']['width']-2*self._settings.get_int(["plate_coner_xy"])
	# 	dy=self.printer_cfg['volume']['depth']-2*self._settings.get_int(["plate_coner_xy"])
	# 	speed=self.printer_cfg['axes']['x']["speed"]

	# 	if(self.levelPos==0):
	# 		dx=0;
	# 	elif(self.levelPos==1):
	# 		dy=0;
	# 	elif(self.levelPos==2):
	# 		dx=0;
	# 		dy=-dy	
	# 	else:
	# 		dx=-dx;
	# 		dy=0	

	# 	self.levelPos+=1;
	# 	if(self.levelPos>3):
	# 		self.levelPos=0

	# 	self.cmdList.addGCode(GCODE_RELATIVEPOSITIONING);
	# 	self.cmdList.addGCode("G0 F{feed} X{dX} Y{dY}".format(feed=speed,dX=dx,dY=dy))
	# 	pass

	# def level_begin(self):
	# 	command=[]
	# 	command.append(GCODE_RELATIVEPOSITIONING)
	# 	command.append(GCODE_MOVE_Z.format(feed=self.printer_cfg['axes']['z']["speed"],dist=self._settings.get_int(["z_travel"])))
	# 	command.append(GCODE_AUTO_HOME.format(axis="X Y"))
	# 	self.cmdList.addGCode(command)
	# 	self.cmdList.addGCode(GCODE_ABSOLUTE_POSITIONING);
	# 	self.cmdList.addGCode(GCODE_MOVE_XY.format(feed=self.printer_cfg['axes']['x']["speed"],
	# 												pos_x=self._settings.get_int(["probe_offset_x"])+self._settings.get_int(["plate_coner_xy"]),
	# 												pos_y=self._settings.get_int(["probe_offset_y"])+self._settings.get_int(["plate_coner_xy"])))
	# 	self.levelPos=0
	# 	pass

#------------------------------------------------------

	def probe_cb_stop_on_error(self,response):
		for line in response:
			if line.startswith("Error:Failed to reach target"):
				self._plugin_manager.send_plugin_message(self._identifier, dict(probe_state='Failed'))
				self.cmdList.clearCommandList()
				return False
		return True

	def probe_cb_echo(self,response):
		for line in response:
			match=re.match("^X:(?P<val_x>-?\d+\.\d+)\sY:(?P<val_y>-?\d+\.\d+)\sZ:(?P<val_z>-?\d+\.\d+)\sE:-?\d+\.\d+",line)
			if(match):
				result="Probe Done Z:{zpos}".format(zpos=match.group('val_z'));
				self._plugin_manager.send_plugin_message(self._identifier, dict(probe_state=result))
				self.cmdList.addGCode("M117 "+result);
				return
		self._plugin_manager.send_plugin_message(self._identifier, dict(probe_state="unproper answer"))
		self._logger.info("unproper answer")
		pass

	def	probe(self,data):
		self._logger.info("probe")
		self._plugin_manager.send_plugin_message(self._identifier, dict(probe_state='probing'))
		self.cmdList.addGCode(GCODE_RELATIVEPOSITIONING)
		#fast probe
		self.cmdList.addGCode("G38.2 F{feed} Z{dist}".format(feed=data["feed"],dist=-1*data["distanse"]),self.probe_cb_stop_on_error)
		#show pos
		self.cmdList.addGCode("M114",self.probe_cb_echo)
		pass

#--------------------------------------------
	def gcode_received_hook(self, comm_instance, line, *args, **kwargs):
		if self.cmdList!=None:
			self.cmdList.processResponce(line)
		return line

	def get_api_commands(self):
		return dict(probe_area=['width','depth','feed_probe','feed_z','feed_xy','grid','level_delta_z'],
					probe=['distanse','feed'])

	def on_api_command(self, command, data):
		self._logger.info("on_api_command:"+command)
		if(command == 'probe_area'):
			pass
		elif(command == 'probe'):
			self.probe(data)


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Cext Plugin"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
#__plugin_pythoncompat__ = ">=2.7,<3" # only python 2
#__plugin_pythoncompat__ = ">=3,<4" # only python 3
#__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = CextPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.comm.protocol.gcode.received":__plugin_implementation__.gcode_received_hook
	}

