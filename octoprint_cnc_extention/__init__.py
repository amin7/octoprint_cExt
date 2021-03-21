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
import io
import math
from collections import deque
import flask
import octoprint.printer

# -------------- const
GCODE_AUTO_HOME = 'G28'
GCODE_ABSOLUTE_POSITIONING = 'G90'
GCODE_RELATIVEPOSITIONING = 'G91'
GCODE_PROBE_UP = "G38.4 F{feed} Z{dist}"
GCODE_PROBE_DOWN = "G38.2 F{feed} Z{dist}"
GCODE_AUTO_HOME = "G28 {axis}"
GCODE_MOVE_XY = "G0 F{feed} X{pos_x} Y{pos_y}"
GCODE_MOVE_Z = "G0 F{feed} Z{dist}"
GCODE_SET_POS_000 = "G92 X0 Y0 Z0"
GCODE_SET_POS_00Z = "G92 X0 Y0 Z{pos_z}"

HTTP_Precondition_Failed = 412

#------------------------
class CCmdList:
	def __init__(self, sendGCode):
		self.sendGCode = sendGCode

	class CCommand:
		def __init__(self, command, callBack=None):
			self.command = command
			self.callBack = callBack

	cmdList = deque()
	processingCommand = None
	response = []

	def clearCommandList(self):
		self.cmdList.clear()

	def processCommandList(self):
		if self.processingCommand == None:
			if self.cmdList:
				self.processingCommand = self.cmdList.popleft()
				self.sendGCode(self.processingCommand.command)
				pass
			pass
		pass

	def addGCode(self, commands, callBack=None):
		if isinstance(commands, list):
			commlen = len(commands)
			for i in range(commlen):
				cmd = self.CCommand(commands[i]);
				if (i == commlen - 1):
					cmd.callBack = callBack
				self.cmdList.append(cmd)
			pass
		else:
			self.cmdList.append(self.CCommand(commands, callBack))
			pass
		self.processCommandList()

	def processResponce(self, response):
		if self.processingCommand != None:
			if not response.startswith("echo:busy: processing"):
				self.response.append(response);
				if (response.startswith('ok')):
					if (self.processingCommand.callBack != None):
						self.processingCommand.callBack(self.response)
					self.processingCommand = None
					self.response = []
					self.processCommandList()


# --------------------------------------------------------------
#
#  *                           z2   --|
#  *                 z0        |      |
#  *                  |        |      + (z2-z1)
#  *   z1             |        |      |
#  * ---+-------------+--------+--  --|
#  *   a1            a0        a2
#  *    |<---delta_a---------->|
#  *
#  *  __calc_z0 is the basis for all the Mesh Based correction. It is used to
#  *  find the expected Z Height at a position between two known Z-Height locations.
#  *
#  *  It is fairly expensive with its 4 floating point additions and 2 floating point
#  *  multiplications.

class CBedLevel:
	def __init__(self, width, depth, grid):
		# round up
		self.m_sizeX = int(math.ceil(float(width) / grid) * grid)
		self.m_sizeY = int(math.ceil(float(depth) / grid) * grid)
		self.m_grid = int(grid)
		self.m_ZheighArray = [[None for x in range(int(self.m_sizeY / grid + 1))] for y in
							  range(int(self.m_sizeX / grid + 1))]

	# protected
	@staticmethod
	def __calc_z0(a0, a1, z1, a2, z2):
		return z1 + (z2 - z1) * (a0 - a1) / (a2 - a1)

	def __cell_index(self, coord, max_coord):
		if coord <= 0:
			return 0
		if coord >= max_coord:
			return int(max_coord / self.m_grid)
		return int(coord / self.m_grid)

	def get_i_x(self, index):
		maxx = self.m_sizeX / self.m_grid
		posx = index % (maxx + 1)
		if self.get_i_y(index) % 2:
			posx = maxx - posx
			pass
		return int(posx)

	def get_i_y(self, index):
		return int(index / (self.m_sizeX / self.m_grid + 1))

	def mesh_z_value(self, mX, mY):
		return self.m_ZheighArray[mX][mY]

	# public

	def set(self, index, z_height):
		self.m_ZheighArray[self.get_i_x(index)][self.get_i_y(index)] = float(z_height);

	def get_count(self):
		if math.isnan(self.m_sizeX) or math.isnan(self.m_sizeY) or math.isnan(self.m_grid):
			return -1
		return int((self.m_sizeX / self.m_grid + 1) * (self.m_sizeY / self.m_grid + 1))

	def get_z_correction(self, rx0, ry0):
		if self.m_sizeX < rx0 or self.m_sizeY < ry0:
			return None

		cx = self.__cell_index(rx0, self.m_sizeX)
		cy = self.__cell_index(ry0, self.m_sizeY)

		mx = cx * self.m_grid
		my = cy * self.m_grid

		if (mx == rx0 and my == ry0):
			# in dot
			return self.mesh_z_value(cx, cy);
		if (mx == rx0):
			# in line X
			return self.__calc_z0(ry0, my, self.mesh_z_value(cx, cy), my + self.m_grid, self.mesh_z_value(cx, cy + 1))

		if (my == ry0):
			# in line Y
			return self.__calc_z0(rx0, mx, self.mesh_z_value(cx, cy), mx + self.m_grid, self.mesh_z_value(cx + 1, cy))
		z1 = self.__calc_z0(rx0, mx, self.mesh_z_value(cx, cy), mx + self.m_grid, self.mesh_z_value(cx + 1, cy))
		z2 = self.__calc_z0(rx0, mx, self.mesh_z_value(cx, cy + 1), mx + self.m_grid, self.mesh_z_value(cx + 1, cy + 1))
		return self.__calc_z0(ry0, my, z1, my + self.m_grid, z2)


# --------------------------------------------------------------
# --------------------------------------------------------------
class CBedLevelControl:
	def __init__(self, cmdList, progress_cb, bedLevel):
		self.cmdList = cmdList
		self.bedLevel = bedLevel
		self.progress_cb = progress_cb
		pass

	def _report(self, data):
		self.progress_cb(dict(CBedLevelControl=data))

	def on_update_front(self, data):
		data['CBedLevelControl'] = dict(step=self.probe_area_step, count=self.bedLevel.get_count(), state=self._state)
		pass

	def on_progress(self, state, payload=None):
		self._state = state
		self._report(
			dict(step=self.probe_area_step, count=self.bedLevel.get_count(), state=self._state, payload=payload))
		self.cmdList.addGCode("M117 {state}: {step}/{count} ".format(state=self._state, step=self.probe_area_step,
																	 count=self.bedLevel.get_count()));
		pass

	def on_error(self, details):
		self._state = "Error"
		self._report(dict(state=self._state, details=details))
		self.cmdList.clearCommandList()
		self.cmdList.addGCode(["M117 Err:{details}".format(details=details), GCODE_RELATIVEPOSITIONING,
							   GCODE_MOVE_Z.format(feed=self.feed_z, dist=self.level_delta_z)])
		pass

	def probe_cb_stop_on_error(self, response):
		for line in response:
			if line.startswith("Error:Failed to reach target"):
				self.on_error("Failed to reach target");
				pass
			pass
		pass

	def probe_cb_coordinates(self, response):
		for line in response:
			match = re.match("^X:(?P<val_x>-?\d+\.\d+)\sY:(?P<val_y>-?\d+\.\d+)\sZ:(?P<val_z>-?\d+\.\d+)\sE:-?\d+\.\d+",
							 line)
			if (match):
				zpos = 0
				if (self.probe_area_step):
					zpos = match.group('val_z')
					pass
				else:
					self.cmdList.addGCode(GCODE_SET_POS_00Z.format(pos_z=self.level_delta_z))  # aftre probe heigh
					pass
				self.bedLevel.set(self.probe_area_step, zpos);
				self.probe_area_step += 1;
				if (self.probe_area_step < self.bedLevel.get_count()):
					self.make_probe()
					self.on_progress("Progress")
					pass
				else:
					self._state="Done";
					self._report(dict(state=self._state, zHeigh=self.bedLevel.m_ZheighArray));
					self.cmdList.addGCode("M117 ProbeArea Done");
					if self._on_done:
						self._on_done()
						pass
					pass
				return
			pass
		self.on_error(response)
		pass

	def make_probe(self):
		# go to pos
		pos_x = self.bedLevel.get_i_x(self.probe_area_step) * self.bedLevel.m_grid
		pos_y = self.bedLevel.get_i_y(self.probe_area_step) * self.bedLevel.m_grid
		self.cmdList.addGCode(
			[GCODE_ABSOLUTE_POSITIONING, GCODE_MOVE_XY.format(feed=self.feed_xy, pos_x=pos_x, pos_y=pos_y)])
		# probe
		self.cmdList.addGCode(
			[GCODE_RELATIVEPOSITIONING, GCODE_PROBE_DOWN.format(feed=self.feed_probe, dist=-2 * self.level_delta_z)],
			self.probe_cb_stop_on_error)
		# save pos
		self.cmdList.addGCode("M114", self.probe_cb_coordinates)
		# hop
		self.cmdList.addGCode(GCODE_MOVE_Z.format(feed=self.feed_z, dist=self.level_delta_z))
		pass

	def stop(self):
		if self._state == "Init" or self._state == "Progress":
			self.cmdList.clearCommandList()
			self.cmdList.addGCode(["M117 Stop", GCODE_RELATIVEPOSITIONING,
								   GCODE_MOVE_Z.format(feed=self.feed_z, dist=self.level_delta_z)])
		self._state = ''
		self._report(dict(state=self._state))
		pass

	def start(self, data, on_done =None):
		self.probe_area_step = 0
		self.feed_probe = data['feed_probe']
		self.feed_z = data['feed_z']
		self.feed_xy = data['feed_xy']
		self.level_delta_z = data['level_delta_z']
		self._on_done= on_done
		self.on_progress("Init")
		# preinit
		self.cmdList.addGCode([GCODE_SET_POS_000, GCODE_RELATIVEPOSITIONING,
							   GCODE_MOVE_Z.format(feed=self.feed_z, dist=self.level_delta_z),
							   GCODE_MOVE_XY.format(feed=self.feed_xy, pos_x=1, pos_y=1)])
		self.make_probe()
		pass

	pass


# --------------------------------------------------------------
# --------------------------------------------------------------
class CProbeControl:
	def __init__(self, cmdList, progress_cb, data):
		self.cmdList = cmdList
		self.progress_cb = progress_cb
		self._report(dict(state='probing {dist}, {feed} mm/s'.format(dist=-1 * data["distanse"],feed=data["feed"])))
		self.cmdList.addGCode(GCODE_RELATIVEPOSITIONING)
		# fast probe
		self.cmdList.addGCode(GCODE_PROBE_DOWN.format(feed=data["feed"], dist=-1 * data["distanse"]),
							  self.cb_stop_on_error)
		# show pos
		self.cmdList.addGCode("M114", self.cb_echo)
		pass

	def _report(self, data):
		self.progress_cb(dict(CProbeControl=data))

	def cb_stop_on_error(self, response):
		for line in response:
			if line.startswith("Error:Failed to reach target"):
				self.cmdList.clearCommandList()
				self._report(dict(state='Failed'))
				pass
		pass

	def cb_echo(self, response):
		for line in response:
			match = re.match("^X:(?P<val_x>-?\d+\.\d+)\sY:(?P<val_y>-?\d+\.\d+)\sZ:(?P<val_z>-?\d+\.\d+)\sE:-?\d+\.\d+",
							 line)
			if (match):
				result = "Probe Done Z:{zpos}".format(zpos=match.group('val_z'));
				self._report(dict(state=result,zpos=match.group('val_z')))
				self.cmdList.addGCode("M117 " + result);
				return
		self._report(dict(state='err_pos', response=response))
		pass

	pass


# --------------------------------------------------------------
def gcode2dict(gcode):
	gcode = gcode.split(";")[0]  # remove comment
	_cmd = re.search("((^.\d+\.\d+)|(^.\d+))", gcode)
	if not _cmd:
		return dict(cmd=None)
	parsed = dict(cmd=_cmd.group())

	pattern="((-?\d+\.\d+)|(-?\d+))"
	_valX = re.search("X"+pattern, gcode)
	_valY = re.search("Y"+pattern, gcode)
	_valZ = re.search("Z"+pattern, gcode)
	_valF = re.search("F"+pattern, gcode)

	if _valX:
		parsed['X'] = float(_valX.group(1))
	if _valY:
		parsed['Y'] = float(_valY.group(1))
	if _valZ:
		parsed['Z'] = float(_valZ.group(1))
	if _valF:
		parsed['F'] = float(_valF.group(1))
	return parsed


def dict2gcode(_dict):
	if "cmd" not in _dict:
		return None
	gcode = _dict['cmd']
	for key in _dict.keys():
		if key != "cmd":
			gcode += " {key}{val}".format(key=key, val=_dict[key])
	return gcode


class CSwapXY:
	def run(self, cmd):
		if cmd.startswith("G0") or cmd.startswith("G1") or cmd.startswith("G92"):
			_cmd = ""
			for i in cmd:
				if i == 'X':
					i = 'Y'
				elif i == 'Y':
					i = 'X'
				_cmd += i
			return _cmd
		return cmd #nothing to change	    
	pass


class CBedLevelAjust:
	def __init__(self, bedLevel, offs_X, offs_Y):
		self._cur_X = 0
		self._cur_Y = 0
		self._cur_Z = 0
		self._offs_X = offs_X
		self._offs_Y = offs_Y
		self._bed_level = bedLevel
		pass

	def __line_z_move(self, g_parsed):
		# Zmove only
		x = self._cur_X
		y = self._cur_Y
		z = self._cur_Z
		if "X" in g_parsed:
			x = g_parsed["X"]
			pass
		if "Y" in g_parsed:
			y = g_parsed["Y"]
			pass
		if "Z" in g_parsed:
			z = g_parsed["Z"]
			pass
		cor_z = self._bed_level.get_z_correction(x, y)
		if cor_z == None:
			return None
		self._cur_X = x
		self._cur_Y = y
		self._cur_Z = z
		g_parsed["Z"] = z + cor_z
		return dict2gcode(g_parsed)

	def run(self, cmd):
		g_parsed = gcode2dict(cmd)
		if g_parsed["cmd"] == "G0" or g_parsed["cmd"] == "G1":
			if "X" not in g_parsed and "Y" not in g_parsed:
				return self.__line_z_move(g_parsed)

			dest_x = self._cur_X
			dest_y = self._cur_Y
			dest_z = self._cur_Z

			# add offet for absolute only
			if "X" in g_parsed:
				dest_x = g_parsed["X"] + self._offs_X
				pass
			if "Y" in g_parsed:
				dest_y = g_parsed["Y"] + self._offs_Y
				pass

			line_len = math.hypot(dest_x - self._cur_X, dest_y - self._cur_Y);
			if 0 == line_len:  # move to same coordinate
				return self.__line_z_move(g_parsed)

			if "Z" in g_parsed:
				dest_Z = g_parsed["Z"]
				pass

			step_div = math.ceil(line_len / self._bed_level.m_grid)
			dx = (dest_x - self._cur_X) / step_div
			dy = (dest_y - self._cur_Y) / step_div
			dz = (dest_z - self._cur_Z) / step_div
			g_parsed["X"] = self._cur_X
			g_parsed["Y"] = self._cur_Y
			g_parsed["Z"] = self._cur_Z
			sublines = []
			while line_len > self._bed_level.m_grid:
				g_parsed["X"] += dx
				g_parsed["Y"] += dy
				g_parsed["Z"] += dz
				line_len -= self._bed_level.m_grid
				sublines.append(self.__line_z_move(g_parsed))
				pass
			g_parsed["X"] = dest_x
			g_parsed["Y"] = dest_y
			g_parsed["Z"] = dest_z
			sublines.append(self.__line_z_move(g_parsed))
			return sublines
		return cmd

	pass


class CAnalising:
	_cur_X = 0
	_cur_Y = 0
	_cur_Z = 0
	_total_lines = 0
	_lines_move = 0
	_min_x = None
	_min_y = None
	_min_z = None
	_max_x = None
	_max_y = None
	_max_z = None

	@staticmethod
	def __upd_min(_min, val):
		if _min is None or _min > val:
			return val
		return _min

	@staticmethod
	def __upd_max(_max, val):
		if _max is None or _max < val:
			return val
		return _max

	@staticmethod
	def __sub(val1, val2):
		if val1 is None or val2 is None:
			return None
		return val1-val2

	def _analising_pos(self):
		self._min_x = self.__upd_min(self._min_x, self._cur_X)
		self._min_y = self.__upd_min(self._min_y, self._cur_Y)
		self._min_z = self.__upd_min(self._min_z, self._cur_Z)
		self._max_x = self.__upd_max(self._max_x, self._cur_X)
		self._max_y = self.__upd_max(self._max_y, self._cur_Y)
		self._max_z = self.__upd_max(self._max_z, self._cur_Z)
		pass

	def add(self, cmd):
		self._total_lines += 1
		g_parsed = gcode2dict(cmd)
		# calk start point
		if g_parsed["cmd"] == "G1":
			self._analising_pos()
			pass
		# update pos
		if g_parsed["cmd"] == "G0" or g_parsed["cmd"] == "G1":
			self._lines_move += 1
			if "X" in g_parsed:
				self._cur_X = g_parsed["X"]
				pass
			if "Y" in g_parsed:
				self._cur_Y = g_parsed["Y"]
				pass
			if "Z" in g_parsed:
				self._cur_Z = g_parsed["Z"]
				pass
			pass
		# calk end point
		if g_parsed["cmd"] == "G1":
			self._analising_pos()
			pass
		pass

	def get_analising(self):
		return dict(width=self.__sub(self._max_x, self._min_x), depth=self.__sub(self._max_y, self._min_y),
					min=dict(x=self._min_x, y=self._min_y, z=self._min_z),
					max=dict(x=self._max_x, y=self._max_y, z=self._max_z),
					line=dict(total=self._total_lines,move= self._lines_move)
					)

	pass


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
			js=["js/cnc_extention.js"],
			css=["css/cnc_extention.css"]
		)

	# ~~ TemplatePlugin mixin

	def get_template_configs(self):
		return [
			dict(type="settings")
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
	_bed_level = None
	probe_area_control = None
	_probe = None
	_swap_xy = None
	_bed_level_ajust = None
	file_selected = None
	_analysis = None
	_is_tab_active=False

	def on_after_startup(self):
		self._logger.info("PluginA starting up")
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
			self.file_selected = dict(origin=payload['origin'], path=payload['path'])
			self._swap_xy = None # no need to send
			self._bed_level = None
			self._analysis = None
			data = dict(file_selected=self.file_selected)
			self._plugin_manager.send_plugin_message(self._identifier, data)
			if self._is_tab_active:
				self._analysis = self.do_analysis(self.file_selected['origin'],self.file_selected['path'],None)
		 		self._plugin_manager.send_plugin_message(self._identifier, dict(analysis = self._analysis))		
				pass
			pass
		elif event == 'PrinterStateChanged':
			# if payload['state_id'] == 'OPERATIONAL' and self._bed_level_ajust:
			# 	self._bed_level_ajust = None
			# 	self._plugin_manager.send_plugin_message(self._identifier, dict(bed_level_ajust = False))
			# 	pass
			pass
		pass

	def _update_front(self):
		data = dict(file_selected=self.file_selected, analysis=self._analysis)
		data['bed_level_ajust'] = True if self._bed_level_ajust else False
		if self.probe_area_control:
			self.probe_area_control.on_update_front(data)
		self._plugin_manager.send_plugin_message(self._identifier, data)
		pass

	def control_progress_cb(self, data):
		self._plugin_manager.send_plugin_message(self._identifier, data)
		pass

	def gcode_received_hook(self, comm_instance, line, *args, **kwargs):
		if self.cmdList is not None:
			self.cmdList.processResponce(line)
		return line

	def gcode_queuing(self, comm_instance, phase, cmd, cmd_type, gcode, subcode=None, tags=None, *args, **kwargs):
	#	self._logger.info(dict(cmd=cmd, type=cmd_type, gcode=gcode))
		if self._swap_xy:
			cmd = self._swap_xy.run(cmd)
			pass
		if self._bed_level_ajust:
			cmd = self._bed_level_ajust.run(cmd)
			pass
		return cmd

	def get_api_commands(self):
		return dict(probe_area=['feed_probe', 'feed_z', 'feed_xy', 'grid', 'level_delta_z'],
					probe=['distanse', 'feed'],
					probe_area_stop=[],
					swap_xy=[],
					engrave=[],
					tab_activate=[],
					tab_deactivate=[],
					status=[])

	def on_api_command(self, command, data):
		self._logger.info("on_api_command:" + command, data)
		response = None
		if command == 'probe_area':
			if self._analysis:
				self._bed_level = CBedLevel(self._analysis['width'], self._analysis['depth'], data['grid'])
				self.probe_area_control = CBedLevelControl(self.cmdList, self.control_progress_cb, self._bed_level)
				self.probe_area_control.start(data)
				pass
			else:
				response= flask.make_response("no _analysis ", HTTP_Precondition_Failed)
				pass
			pass
		if command == 'probe_area_stop':
			if self.probe_area_control:
				self.probe_area_control.stop()
				pass
			self._bed_level = None
			self._bed_level_ajust = None
			pass
		elif command == 'probe':
			self._probe = CProbeControl(self.cmdList, self.control_progress_cb, data)
			pass
		elif command == 'swap_xy':
			if self._swap_xy:
				self._swap_xy = None
			else:
				self._swap_xy = CSwapXY()
			self._bed_level = None
			self._analysis = None
			data = dict(analysis=self._analysis,bed_level=self._bed_level)
			self._plugin_manager.send_plugin_message(self._identifier, data)
	
			self._analysis = self.do_analysis(self.file_selected['origin'],self.file_selected['path'],[self._swap_xy])
	 		self._plugin_manager.send_plugin_message(self._identifier, dict(analysis = self._analysis))		

			pass
		elif command == 'engrave':
			if self._bed_level and self._analysis:
				self._bed_level_ajust = CBedLevelAjust(self._bed_level, self._analysis['min']['x'], self._analysis['min']['y'])
				self._printer.start_print()
			else:
				response= flask.make_response("no _bed_level or _analysis ", HTTP_Precondition_Failed)
				pass
			pass
		elif command == 'tab_activate':
			self._is_tab_active=True
			if self.file_selected and self._analysis==None:
				self._analysis = self.do_analysis(self.file_selected['origin'],self.file_selected['path'],[self._swap_xy])
				self._plugin_manager.send_plugin_message(self._identifier, dict(analysis = self._analysis))		
				pass
			pass 
		elif command == 'tab_deactivate':
			self._is_tab_active=False
			pass 
		# elif command == 'analysis':
		# 	if self.file_selected:
		# 		self._analysis = self.do_analysis(self.file_selected['origin'],self.file_selected['path'],self._swap_xy,None)
		# 		self._plugin_manager.send_plugin_message(self._identifier, dict(analysis = self._analysis))
		# 		pass
		# 	else:
		# 		response= flask.make_response("no file_selected", HTTP_Precondition_Failed)
		# 		pass
		# 	pass
		elif command == 'status':
			self._update_front()
			pass
		else:
			self._logger.error("no cmd:"+command)
			pass
		return response

	def do_analysis(self, origin, path, transforms):
		path_on_disk = self._file_manager.path_on_disk(origin,path)
		with io.open(path_on_disk, mode='r', encoding="utf-8", errors="replace") as file_stream:
			analysis = CAnalising()
			for line in file_stream:
				if transforms:
					for trans in transforms:
						line = trans.run(line)
						pass
					pass
				analysis.add(line)
				pass
			return analysis.get_analising()
		return None


# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
# __plugin_pythoncompat__ = ">=2.7,<3" # only python 2
# __plugin_pythoncompat__ = ">=3,<4" # only python 3
# __plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

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
	__plugin_settings_overlay__ = dict(appearance=dict(
		components=dict(order=dict(tab=["temperature", "control", "gcodeviewer", "terminal", "plugin_cExt"]))))


# test


def sendGCode(response):
	print("send :" + response)
	pass


# class CCext_test:
class TEST_file_manager:
	_analysis = None

	def has_analysis(self, a1, a2):
		return self._analysis != None

	def get_metadata(self, m_origin, _path):
		return dict(analysis=_analysis)

	pass


if __name__ == '__main__':
	from inspect import getframeinfo, stack


	def test_isEQ(v1, v2):
		if v1 != v2:
			caller = getframeinfo(stack()[1][0])
			print "{file}:{line} ERROR {v1} != {v2}".format(file=caller.filename, line=caller.lineno, v1=v1, v2=v2)
			pass
		pass


	def test_line(msg=None):
		caller = getframeinfo(stack()[1][0])
		print "{file}:{line} {msg}".format(file=caller.filename, line=caller.lineno, msg=msg)
		pass


	def testCB(response):
		print(response)
		pass


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
	level = CBedLevel(9, 15, 5)
	test_isEQ(level.get_count(), 12)
	level = CBedLevel(10, 11, 5)
	test_isEQ(level.get_count(), 12)
	level = CBedLevel(10, 15, 5)
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
	gc = gcode2dict("G1.1")
	test_isEQ(gc['cmd'], "G1.1")
	gc = gcode2dict("G11")
	test_isEQ(gc['cmd'], "G11")

	gc = gcode2dict("G11 X10; X20")
	test_isEQ(gc['cmd'], "G11")
	test_isEQ(gc['X'], 10)

	gc = gcode2dict("G13 X1 Y10.2 Z23 F500")
	test_isEQ(gc['cmd'], "G13")
	test_isEQ(gc['X'], 1)
	test_isEQ(gc['Y'], 10.2)
	test_isEQ(gc['Z'], 23)
	test_isEQ(gc['F'], 500)

	test_isEQ(dict2gcode(gc), "G13 Y10.2 X1.0 Z23.0 F500.0")

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
