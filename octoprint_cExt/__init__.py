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

	def clearCommandList():
		self.cmdList.clear()

	def processCommandList(self):
		if self.processingCommand==None:
			if self.cmdList:
				self.processingCommand=self.cmdList.popleft()
				self.sendGCode(self.processingCommand.command)	
				#self._printer.commands(
				#send cmd


	def addGCode(self,commands,callBack = None):
		commlen=len(commands)
		for i in range(commlen):
			cmd=self.CCommand(commands[i]);
			if(i==commlen-1):
				cmd.callBack=callBack
			self.cmdList.append(cmd)
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

cmd_RelativePositioning ='G91'

class CextPlugin(octoprint.plugin.SettingsPlugin,
                 octoprint.plugin.AssetPlugin,
                 octoprint.plugin.TemplatePlugin,
                 octoprint.plugin.SimpleApiPlugin,
                 octoprint.plugin.StartupPlugin):

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			speed_probe_fast=20,
			speed_probe_fine=10,
			probe_offset_x=10,
			probe_offset_y=10,
			plate_coner_xy=20,
			z_travel=10,
			z_probe_threshold=1,
			auto_next=True,
			auto_threshold=0.1,
			auto_count=3
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

	def on_after_startup(self):
		self.cmdList = CCmdList(self._printer.commands)
		self.printer_cfg=self._printer_profile_manager.get_current()
		self._logger.info("PluginA starting up")
		self._logger.info(self._printer_profile_manager.get_current())
		self._logger.info(self._settings)

	def level_begin_cb1(self,response):
		self._logger.info("level_begin_cb1" + response)

	def level_begin(self):
		self._logger.info("level_begin")
		command = cmd_RelativePositioning+'\n'
		command+="G38.2 F{feed} Z{dist}".format(feed=200,dist=-20);
		self.cmdList.addGCode(command,self.level_begin_cb1)
#------------------------------------------------------
	def probe_cb2(self,response):
		self._logger.info(["probe_cb2", response])

	def probe_cb1(self,response):
		self._logger.info(["probe_cb1", response])
		for line in response:
			if line.startswith("Error:Failed to reach target"):
				return
		command =[]
		command.append("G0 F{feed} Z{dist}".format(feed=self.printer_cfg['axes']['z']["speed"],dist=self._settings.get_int(["z_probe_threshold"])));
		command.append("G38.2 F{feed} Z{dist}".format(feed=self._settings.get_int(["speed_probe_fine"]),dist=-2*self._settings.get_int(["z_probe_threshold"])));
		self.cmdList.addGCode(command,self.probe_cb2)

	def	probe(self,data):
		self._logger.info("probe")
		command =[]
		command.append(cmd_RelativePositioning)
		command.append("G38.2 F{feed} Z{dist}".format(feed=self._settings.get_int(["speed_probe_fast"]),dist=data["distanse"]));
		self.cmdList.addGCode(command,self.probe_cb1)
#--------------------------------------------
	def gcode_received_hook(self, comm_instance, line, *args, **kwargs):
		if self.cmdList!=None:
			self.cmdList.processResponce(line)
		return line

	def get_api_commands(self):
		return dict(levelBegin=[],
					probe=['distanse'])

	def on_api_command(self, command, data):
		self._logger.info("on_api_command")
		if(command == 'levelBegin'):
			self.level_begin()
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

