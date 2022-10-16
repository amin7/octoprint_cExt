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
import io
import math
from collections import deque
import flask
import octoprint.printer

from .utils import *
from .cmdlist import *
from .bedlevel import *
from .controls import *


# --------------------------------------------------------------
# --------------------------------------------------------------
class CextPlugin(octoprint.plugin.SettingsPlugin,
				 octoprint.plugin.AssetPlugin,
				 octoprint.plugin.TemplatePlugin,
				 octoprint.plugin.SimpleApiPlugin,
				 octoprint.plugin.StartupPlugin,
				 octoprint.plugin.EventHandlerPlugin):

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			speed_probe=40,
			z_threshold=1,
			z_travel=10,
			level_delta_z=1,
			grid_area=10,
			feed_xy=500,
			feed_z=100,
			probe_area_feed_xy=800,
			mill_clearance=1
		)

	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/cnc_extention.js"],
			css=["css/cnc_extention.css"]
		)

	# ~~ TemplatePlugin mixin

	def get_template_configs(self):
		return [
			dict(type="settings", custom_bindings=False)
		]

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
		# for details.
		return dict(
			cExt=dict(
				displayName="cncExtention",
				displayVersion=self._plugin_version,
				current=self._plugin_version,
				# update method: pip
				pip="https://github.com/you/octoprint_cExt/archive/{target_version}.zip"
			)
		)

	cmdList = None
	_z_level_map = None
	probe_area_control = None
	_probe = None
	_swap_xy = None
	_offset_xy = None 
	_bed_level_ajust = None
	_file_selected = None
	_analysis = None
	_plane = None
	_is_tab_active=False
	_is_engrave_ready=False
	_engrave_assist =None

	def on_after_startup(self):
		self._logger.info("cnc_extention starting up")
		self._logger.info(self._printer_profile_manager.get_current())
		self._logger.info(self._settings)
		self.cmdList = CCmdList(self._printer.commands)
		self._logger.info(self._file_manager)
		pass

	def on_event(self, event, payload):
		self._logger.info(event)
		self._logger.info(payload)
		if (event == 'UserLoggedIn'):
			self._update_front() #update status on front
			pass
		elif event == 'FileSelected':
			self._file_selected = dict(origin=payload['origin'], path=payload['path'])
			self._clear_data_file(dict(file_selected=self._file_selected ))
			self._calculate()
			pass
		elif event == 'FileDeselected':
			self._file_selected = None
			self._clear_data_file(dict(file_selected=None ))
			self._calculate()
			pass
		elif event in ['PrintFailed','PrintDone','PrintCancelled']: #finish print
			if self._engrave_assist:
				self._engrave_assist = None
				self._plugin_manager.send_plugin_message(self._identifier, dict(engrave_assist=None))
				pass
			pass
		elif event == 'SettingsUpdated':
			if self._plane and self._plane['grid'] is not int(self._settings.get(['grid_area'])):
				self._clear_data_plane();
				self._calculate()
				pass
			pass
		pass

	def _update_front(self):
		data = dict(file_selected=self._file_selected, analysis=self._analysis,is_engrave_ready=self._is_engrave_ready)
		data['plane'] = self._plane
		data['engrave_assist'] = self._engrave_assist is not None
		data['z_level_map'] = self._z_level_map.m_ZheighArray if self._z_level_map else None
		
		if self.probe_area_control:
			self.probe_area_control.on_update_front(data)
		else:
			data['CBedLevelControl'] = None
		self._plugin_manager.send_plugin_message(self._identifier, data)
		pass

	def _clear_data_file(self,data=dict()):
		self._analysis = None
		self._is_engrave_ready = False
		data["analysis"]=None
		data["is_engrave_ready"]=False
		self._plugin_manager.send_plugin_message(self._identifier, data)		
		pass

	def _clear_data_plane(self,data=dict()):
		self._plane = None
		data["plane"]=None
		self._clear_data_probe(data)
		pass
	
	def _clear_data_probe(self,data=dict()):
		self._is_engrave_ready = False
		self._z_level_map = None
		data["z_level_map"]=None
		data["is_engrave_ready"]=False
		self._plugin_manager.send_plugin_message(self._identifier, data)	
		pass

	def _calculate(self):
		data=dict();

		if self._file_selected and not self._analysis and self._is_tab_active:
			self._analysis = self.do_analysis(self._file_selected['origin'],self._file_selected['path'],None)
			if self._plane:
				#check if it mach plane
				pass
			data['analysis'] = self._analysis
			pass

		if not self._plane and self._analysis:
			self._plane=dict()
			self._plane['filename']=self._analysis['filename']
			self._plane['offset']=dict()
			self._plane['offset']['x']=self._analysis['min']['x']
			self._plane['offset']['y']=self._analysis['min']['y']
			self._plane['swap_xy']=False
			grid_area=int(self._settings.get(['grid_area']))
			self._plane['grid']=grid_area
			self._plane['width']=roundToGrid(grid_area,self._analysis['width'])
			self._plane['depth']=roundToGrid(grid_area,self._analysis['depth'])
			data['plane'] = self._plane
			pass 

		if 	not self._is_engrave_ready and self._z_level_map:
			self._is_engrave_ready = True
			data['is_engrave_ready'] =self._is_engrave_ready
			data['z_level_map'] =self._z_level_map.m_ZheighArray
			data['dry_run']  = self.do_analysis(self._file_selected['origin'],self._file_selected['path'],[self._offset_xy,self._swap_xy,CBedLevelAjust(self._z_level_map)])
			pass

		if data: # is not empty
			self._plugin_manager.send_plugin_message(self._identifier, data)	
		pass

	def control_progress_cb(self, data):
		self._plugin_manager.send_plugin_message(self._identifier, data)
		pass

	def on_aftrer_probe_area_done(self,z_level_map):
		self._z_level_map=z_level_map
		self._calculate()
		pass

	def gcode_received_hook(self, comm_instance, line, *args, **kwargs):
		if self.cmdList is not None:
			self.cmdList.processResponce(line)
		return line

	def gcode_queuing(self, comm_instance, phase, cmd, cmd_type, gcode, subcode=None, tags=None, *args, **kwargs):
	#	self._logger.info(dict(cmd=cmd, type=cmd_type, gcode=gcode))
		if self._engrave_assist: #engarve active
			cmd = self._engrave_assist.run(cmd)
			pass
		return cmd

	def get_api_commands(self):
		return dict(probe_area=['feed_probe', 'feed_z', 'feed_xy', 'level_delta_z'],
					probe=['distanse', 'feed'],
					probe_area_stop=[],
					probe_area_skip=[],
					swap_xy=[],
					engrave=[],
					tab_activate=[],
					tab_deactivate=[],
					status=[],
					plane_reset=[],
					apply_xy_offset=[])

	def on_api_command(self, command, data):
		self._logger.info("on_api_command:" + command, data)
		response = None
		if command == 'probe_area':
			if self._plane:
				self._clear_data_probe()
				self.probe_area_control = CBedLevelControl(self.cmdList, self.control_progress_cb, CBedLevel(self._plane))
				self.probe_area_control.start(data,self.on_aftrer_probe_area_done)
				pass
			pass
		if command == 'probe_area_stop':
			if self.probe_area_control:
				self.probe_area_control.stop()
				pass
			self._clear_data_probe()
			pass
		elif command == 'probe_area_skip':
			if self._analysis:
				self._z_level_map = CBedLevel(self._plane,0)
				self._calculate()
				pass
			pass
		elif command == 'probe':
			self._probe = CProbeControl(self.cmdList, self.control_progress_cb, data)
			pass
		elif command == 'engrave':
			if self._is_engrave_ready:
				self._engrave_assist = CMultyRun([self._offset_xy, self._swap_xy, CBedLevelAjust( self._z_level_map)])
				self._plugin_manager.send_plugin_message(self._identifier, dict(engrave_assist=True))
				self._printer.start_print()
				pass
			pass
		elif command == 'tab_activate':
			self._is_tab_active=True
			self._calculate();
			pass 
		elif command == 'tab_deactivate':
			self._is_tab_active = False
			pass 
		elif command == 'status':
			self._update_front()
			pass
		elif command == 'plane_reset':
			self._swap_xy = None
			self._offset_xy = None
			self._clear_data_plane()
			self._calculate()
			pass
		elif command == 'swap_xy':
			self._swap_xy= None if self._swap_xy else CSwapXY()
			self._clear_data_plane()
			self._calculate();
			pass
		elif command == 'apply_xy_offset':
			if self._analysis:
				self._offset_xy = None if self._offset_xy else COffsetXY(-self._analysis['min']['x'],-self._analysis['min']['y'])
				self._clear_data_plane()
				self._calculate();
				pass
			pass
		else:
			self._logger.error("no cmd:"+command)
			pass
		return response

	def do_analysis(self, origin, path, transforms):
		path_on_disk = self._file_manager.path_on_disk(origin,path)
		with io.open(path_on_disk, mode='r', encoding="utf-8", errors="replace") as file_stream:
			runer = CMultyRun(transforms)
			analysis = CAnalising()
			for line in file_stream:
				line=runer.run(line)
				analysis.add(line)
				pass
			result=analysis.get_analising()
			result['filename']=path
			return result
		return None


__plugin_pythoncompat__ = ">=3,<4" # only python 3

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = CextPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.comm.protocol.gcode.received": __plugin_implementation__.gcode_received_hook,
		"octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.gcode_queuing
	}

	# show tabs
	global __plugin_settings_overlay__
	# __plugin_settings_overlay__ = dict(appearance=dict(
	# 	components=dict(order=dict(tab=["temperature", "control", "gcodeviewer", "terminal", "plugin_cExt"]))))



if __name__ == '__main__':
	from inspect import getframeinfo, stack




	print("test begin")
	# test1.py executed as script
	# do something
	cmdList = CCmdList(sendGCode)
	# test.addGCode("G10\n\nF20",testCB)
	# print(test.cmdList)
	# test.processResponce("ok")
	# print(test.cmdList)
	# test.processResponce("ok")
	# print(test.cmdList)
	test_line()
	probe_control = CProbeControl(cmdList, testCB, dict(feed=100, distanse=5))
	test_line()
	level = CBedLevel(dict(width=10,depth=15, grid=5))
	test_isEQ(level.get_count(), 12)
	print(level.m_ZheighArray)
	for i in range(level.get_count()):
		print(i, " ", level.get_i_x(i), " ", level.get_i_y(i))
		level.set(i, i)
	print(level.m_ZheighArray)
	test_line()
	bed_level_control = CBedLevelControl(cmdList, testCB, level)
	test_line()

	# control = CBedLevelControl(cmdList, testCB, level)
	# control._file_manager=	TEST_file_manager()
	# control.on_event('FileSelected', dict(origin='origin',path='path'))
	# # control.on_event('path','origin',dict({u'estimatedPrintTime': 1433.505594528735, u'printingArea': {u'maxZ': 1.9, u'maxX': 185.087, u'maxY': 119.362, u'minX': 14.909, u'minY': 80.628, u'minZ': 0.3}, u'dimensions': {u'width': 170.178, u'depth': 38.733999999999995, u'height': 1.5999999999999999}, u'filament': {u'tool0': {u'volume': 0.0, u'length': 1459.9454600000004}}}))
	# data =dict()
	# control.on_update_front(data)
	# print(data)
	# control._width=30
	# control._depth=10
	bed_level_control.start(dict(feed_probe=40, feed_z=300, feed_xy=500, level_delta_z=0.5, grid=10))
	#
	# print(level.m_ZheighArray)
	# control.cmdList.processResponce("ok")
	# control.cmdList.processResponce("ok")
	# control.cmdList.processResponce("ok")
	# while True:
	# 	control.cmdList.processResponce("X:216.00 Y:205.00 Z:0.00 E:0.00 Count A:34560 B:32800 Z:0")
	# 	control.cmdList.processResponce("ok")
	# 	if(control._state!="Init" and control._state!="Progress"):
	# 		break
	# print(level.m_ZheighArray)
	# print(level.get_z_correction(0,0))
	

	test_line()
	engrave = CBedLevelAjust(level, 0, 0)
	test_isEQ(engrave.run("G1 X0 Y0"), "G1 Y0.0 X0.0 Z0")
	test_isEQ(engrave.run("G1 X5 Y5"), ['G1 Y2.5 X2.5 Z2.5', 'G1 Y5.0 X5.0 Z4'])
	test_isEQ(engrave.run("G1 Z1"), "G1 Z5.0")

	test_line()
	analising = CAnalising()
	analising.add("G0 X10")
	analising.add("G1 Y20 Z-1")
	print(analising.get_analising())
	test_isEQ(analising.get_analising()['max']['z'], 0)
	test_isEQ(analising.get_analising()['min']['z'], -1)
	print("test end ")
