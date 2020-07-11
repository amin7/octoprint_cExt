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

import math
from collections import deque
#-------------- const
GCODE_ABSOLUTE_POSITIONING ='G90'
GCODE_RELATIVEPOSITIONING ='G91'
GCODE_PROBE_UP="G38.4 F{feed} Z{dist}"
GCODE_PROBE_DOWN="G38.2 F{feed} Z{dist}"
GCODE_AUTO_HOME="G28 {axis}"
GCODE_MOVE_XY="G0 F{feed} X{pos_x} Y{pos_y}"
GCODE_MOVE_Z="G0 F{feed} Z{dist}"
GCODE_SET_POS_000="G92 X0 Y0 Z0"
GCODE_SET_POS_00Z="G92 X0 Y0 Z{pos_z}"

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
				pass
			pass
		pass

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

#--------------------------------------------------------------
#
#  *                           z2   --|
#  *                 z0        |      |
#  *                  |        |      + (z2-z1)
#  *   z1             |        |      |
#  * ---+-------------+--------+--  --|
#  *   a1            a0        a2
#  *    |<---delta_a---------->|
#  *
#  *  calc_z0 is the basis for all the Mesh Based correction. It is used to
#  *  find the expected Z Height at a position between two known Z-Height locations.
#  *
#  *  It is fairly expensive with its 4 floating point additions and 2 floating point
#  *  multiplications.

class CBedLevel:
	m_sizeX=float('nan')
	m_sizeY=float('nan')
	m_grid=float('nan')
	m_ZheighArray=None
	#protected
	def calc_z0(a0, a1, z1, a2, z2):
		return z1 + (z2 - z1) * (a0 - a1) / (a2 - a1)

	def cell_index(self,coord,max):
		if (coord <= 0):
			return 0;
		if (coord >= max):
			return max / self.m_grid;
		return coord / self.m_grid;

	def cell_index_x(self,coord):
		return self.cell_index(coord, self.m_sizeX);

	def cell_index_y(self,coord):
		return self.cell_index(coord, self.m_sizeY);

	def get_i_x(self, index):
		maxx=self.m_sizeX/self.m_grid
		posx=index%(maxx+1)
		if self.get_i_y(index)%2:
			posx=maxx-posx
			pass
		return int(posx)

	def get_i_y(self, index):
		return int(index/(self.m_sizeX/self.m_grid+1))

	def mesh_z_value(self,mX, mY):
		return self.m_ZheighArray[mX][mY]

   #public
	def init(self,width,depth,grid):
		# round up
		self.m_sizeX=int((width+grid)/grid)*grid
		self.m_sizeY=int((depth+grid)/grid)*grid
		self.m_grid=grid
		self.m_ZheighArray = [[float('nan') for x in range(int(self.m_sizeY/grid+1))] for y in range(int(self.m_sizeX/grid+1))]

	def set(self, index, z_height):
		self.m_ZheighArray[self.get_i_x(index)][self.get_i_y(index)]=z_height;

	def get_count(self):
		if math.isnan(self.m_sizeX) or math.isnan(self.m_sizeY) or math.isnan(self.m_grid):
			return -1
		return int((self.m_sizeX/self.m_grid+1)*(self.m_sizeY/self.m_grid+1))

	def get_z_correction(self, rx0, ry0):

		if  self.m_sizeX < rx0 or self.m_sizeY < ry0:
			return float('nan')

		cx = self.cell_index(rx0, self.m_sizeX);
		cy = self.cell_index(ry0, self.m_sizeY);

		mx = cx * self.m_grid;
		my = cy * self.m_grid;

		if (mx == rx0 and my == ry0):
			#in dot
			return self.mesh_z_value(cx, cy);
		if (mx == rx0):
			#in line X
			return self.calc_z0(ry0, my, self.mesh_z_value(cx, cy), my + self.m_grid, self.mesh_z_value(cx, cy + 1))

		if (my == ry0):
			#in line Y
			return self.calc_z0(rx0, mx, self.mesh_z_value(cx, cy),  mx + self.m_grid, self.mesh_z_value(cx + 1, cy))
		z1 = celf.calc_z0(rx0, mx, self.mesh_z_value(cx, cy), mx + self.m_grid, self.mesh_z_value(cx + 1, cy))
		z2 = self.calc_z0(rx0, mx, self.mesh_z_value(cx, cy + 1), mx + self.m_grid, self.mesh_z_value(cx + 1, cy + 1))
		return self.calc_z0(ry0, my, z1, my + self.m_grid, z2)

#--------------------------------------------------------------
#--------------------------------------------------------------
class CBedLevelComtrol:
	def __init__(self,cmdList,progress_cb,bedLevel):
		self.cmdList=cmdList
		self.bedLevel=bedLevel
		self.progress_cb=progress_cb
		self.on_init()
		pass

	def _report(self,data):
		self.progress_cb(dict(CBedLevelComtrol=data))

	def on_init(self):
		self._path = None
		self._origin = None
		self._width = None
		self._depth = None
		self._min_x = None
		self._min_y = None
		self.probe_area_step = None
		self._state = None
		pass

	def on_event(self, event, payload):
		if (event == 'FileSelected'):
			self._origin = payload['origin']
			self._path = payload['path']
			if self._file_manager.has_analysis(self._origin, self._path):
				analysis = self._file_manager.get_metadata(self._origin, self._path)['analysis']
				cext._logger.info(analysis)
				self._width = analysis['dimensions']['width']
				self._depth = analysis['dimensions']['depth']
				self._min_x = analysis['printingArea']['minX']
				self._min_y = analysis['printingArea']['minY']
				pass
			data=dict()
			self.on_update_front(data)
			self.progress_cb(data)
			pass
		pass

	def on_update_front(self,data):
		data['CBedLevelComtrol']=dict(state=self._state,path=self._path, width=self._width, depth=self._depth)
		pass

	def on_progress(self,state,payload=None):
		self._state=state
		self._report(dict(step=self.probe_area_step,count=self.bedLevel.get_count(),state=self._state,payload=payload))
		self.cmdList.addGCode("M117 {state}: {step}/{count} ".format(state=self._state,step=self.probe_area_step,count=self.bedLevel.get_count()));
		pass

	def on_error(self,err,payload=None):
		self._state=err
		self._report(dict(state=self._state,payload=payload))
		self.cmdList.clearCommandList()
		self.cmdList.addGCode(["M117 Err:{state}".format(state=self._state),GCODE_RELATIVEPOSITIONING, GCODE_MOVE_Z.format(feed=self.feed_z,dist=self.level_delta_z)])
		pass

	def probe_cb_stop_on_error(self,response):
		for line in response:
			if line.startswith("Error:Failed to reach target"):
				self.on_error("Error:Failed to reach target");
				pass
			pass
		pass

	def probe_cb_coordinates(self,response):
		for line in response:
			match=re.match("^X:(?P<val_x>-?\d+\.\d+)\sY:(?P<val_y>-?\d+\.\d+)\sZ:(?P<val_z>-?\d+\.\d+)\sE:-?\d+\.\d+",line)
			if(match):
				zpos=0
				if(self.probe_area_step):
					zpos=match.group('val_z');
				else:
					self.cmdList.addGCode(GCODE_SET_POS_00Z.format(pos_z=self.level_delta_z))#aftre probe heigh
				self.bedLevel.set(self.probe_area_step,zpos);
				self.probe_area_step+=1;
				if(self.probe_area_step<self.bedLevel.get_count()):
					self.make_probe()
					self.on_progress("Progress")
				else:
					self.on_progress("Done",self.bedLevel.m_ZheighArray)
				return
			pass
		self.on_error("err pos",response)
		pass

	def make_probe(self):
		#go to pos
		pos_x=self.bedLevel.get_i_x(self.probe_area_step)*self.bedLevel.m_grid
		pos_y=self.bedLevel.get_i_y(self.probe_area_step)*self.bedLevel.m_grid
		self.cmdList.addGCode([GCODE_ABSOLUTE_POSITIONING, GCODE_MOVE_XY.format(feed=self.feed_xy,pos_x=pos_x,pos_y=pos_y)])
		#probe
		self.cmdList.addGCode([GCODE_RELATIVEPOSITIONING, GCODE_PROBE_DOWN.format(feed=self.feed_probe,dist=-2*self.level_delta_z)],self.probe_cb_stop_on_error)
		#save pos
		self.cmdList.addGCode("M114",self.probe_cb_coordinates)
		#hop
		self.cmdList.addGCode(GCODE_MOVE_Z.format(feed=self.feed_z,dist=self.level_delta_z))
		pass

	def stop(self):
		if self._state== "Init" or self._state== "Progress":
			self.cmdList.clearCommandList()
			self.cmdList.addGCode(["M117 Stop",GCODE_RELATIVEPOSITIONING, GCODE_MOVE_Z.format(feed=self.feed_z,dist=self.level_delta_z)])
		self._state=''
		self._report(dict(state=self._state))
		pass

	def start(self,data):
		if self._width == None or self._depth == None:
			self.on_progress("not inited")
			return
		self.probe_area_step=0
		self.feed_probe=data['feed_probe']
		self.feed_z=data['feed_z']
		self.feed_xy=data['feed_xy']
		self.level_delta_z=data['level_delta_z']
		self.bedLevel.init(self._width,self._depth,data['grid'])
		self.on_progress("Init")
		#preinit
		self.cmdList.addGCode([GCODE_SET_POS_000,GCODE_RELATIVEPOSITIONING,GCODE_MOVE_Z.format(feed=self.feed_z,dist=self.level_delta_z), GCODE_MOVE_XY.format(feed=self.feed_xy,pos_x=1,pos_y=1)])
		self.make_probe()
		pass
	def engrave(self):
		pass

#--------------------------------------------------------------
#--------------------------------------------------------------
class CProbeControl:
	def __init__(self,cmdList,progress_cb):
		self.cmdList=cmdList
		self.progress_cb=progress_cb
		pass

	def _report(self,data):
		self.progress_cb(dict(CProbeComtrol=data))

	def cb_stop_on_error(self,response):
		for line in response:
			if line.startswith("Error:Failed to reach target"):
				self.cmdList.clearCommandList()
				self._report(dict(state='Failed'))
				pass
		pass

	def cb_echo(self,response):
		for line in response:
			match=re.match("^X:(?P<val_x>-?\d+\.\d+)\sY:(?P<val_y>-?\d+\.\d+)\sZ:(?P<val_z>-?\d+\.\d+)\sE:-?\d+\.\d+",line)
			if(match):
				result="Probe Done Z:{zpos}".format(zpos=match.group('val_z'));
				self._report(dict(state=result))
				self.cmdList.addGCode("M117 "+result);
				return
		self._report(dict(state='err_pos',response=response))
		pass

	def start(self,data):
		self._report(dict(state='probing'))
		self.cmdList.addGCode(GCODE_RELATIVEPOSITIONING)
		#fast probe
		self.cmdList.addGCode(GCODE_PROBE_DOWN.format(feed=data["feed"],dist=-1*data["distanse"]),self.cb_stop_on_error)
		#show pos
		self.cmdList.addGCode("M114",self.cb_echo)
		pass
#--------------------------------------------------------------
#--------------------------------------------------------------
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
	probe_area_control=None
	probe=None
	is_swap_xy=False
	is_apply_probe_data=False

	def on_after_startup(self):
		self._logger.info("PluginA starting up")
		self._logger.info(self._printer_profile_manager.get_current())
		self._logger.info(self._settings)
		self.cmdList = CCmdList(self._printer.commands)
		self.level=CBedLevel()
		self.probe_area_control=CBedLevelComtrol(self.cmdList, self.control_progress_cb, self.level, self._file_manager)
		self.probe=CProbeComtrol(self.cmdList,self.control_progress_cb)
		pass

	def on_event(self, event, payload):
		self._logger.info(event)
		self._logger.info(payload)
		if self.probe_area_control:
			self.probe_area_control.on_event(self, event, payload)
		if(event=='UserLoggedIn'):
			self._update_front()
		return
		pass

	def _update_front(self):
		data=dict()
		if self.probe_area_control:
			self.probe_area_control.on_update_front(data)
		self._plugin_manager.send_plugin_message(self._identifier, data)
		pass

	def control_progress_cb(self,data):
		self._plugin_manager.send_plugin_message(self._identifier, data)
		pass

#----------------------------------
	#                                               pos_x=self._settings.get_int(["probe_offset_x"])+self._settings.get_int(["plate_coner_xy"]),
	#                                               pos_y=self._settings.get_int(["probe_offset_y"])+self._settings.get_int(["plate_coner_xy"])))

#--------------------------------------------
	def gcode_received_hook(self, comm_instance, line, *args, **kwargs):
		if self.cmdList!=None:
			self.cmdList.processResponce(line)
		return line

	def gcode_queuing(self, comm_instance, phase, cmd, cmd_type, gcode, subcode=None, tags=None, *args, **kwargs):
		self._logger.info(dict(cmd=cmd,type=cmd_type,gcode=gcode))
		if self.is_swap_xy:
			if gcode=="G0" or gcode == "G1" or gcode=="G92":
				_cmd=""
				for i in cmd:
					if i=='X':
						i='Y'
					elif i=='Y':
						i='X'
					_cmd+=i
				cmd=_cmd
				pass
			pass

		if self.is_apply_probe_data:
			pass

		return cmd

	def get_api_commands(self):
		return dict(probe_area=['feed_probe','feed_z','feed_xy','grid','level_delta_z'],
					probe=['distanse','feed'],
					probe_area_stop=[],
					swap_xy=['active'])

	def on_api_command(self, command, data):
		self._logger.info("on_api_command:"+command)
		if(command == 'probe_area'):
			if self.probe_area_control:
				self.probe_area_control.start(data)
			pass
		if(command == 'probe_area_stop'):
			if self.probe_area_control:
				self.probe_area_control.stop()
			pass
		elif(command == 'probe'):
			if self.probe:
				self.probe.start(data)
			pass
		elif(command == 'swap_xy'):
			self.is_swap_xy=(data['active'])
		elif(command == 'engrave'):
			self.eng


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
		"octoprint.comm.protocol.gcode.received":__plugin_implementation__.gcode_received_hook,
		"octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.gcode_queuing
	}


# test
def testCB(response):
	print(response)

def sendGCode(response):
	print("send :" + response)
	pass

#class CCext_test:
class TEST_file_manager:
	_analysis =None
	def has_analysis(self,a1,a2):
		return self._analysis!=None
	def get_metadata(self,m_origin,_path):
		return dict(analysis=_analysis)
	pass

if __name__ == '__main__':
	print("test begin")
	# test1.py executed as script
	# do something
	cmdList=CCmdList(sendGCode)
	# test.addGCode("G10\n\nF20",testCB)
	# print(test.cmdList)
	# test.processResponce("ok")
	# print(test.cmdList)
	# test.processResponce("ok")
	# print(test.cmdList)

	level=CBedLevel()
	# level.init(10,15,5)
	# print("sz:"+str(level.get_count()));
	# print(level.m_ZheighArray)
	# for i in range(level.get_count()):
	#   print(i," ",level.get_i_x(i)," ",level.get_i_y(i))
	#   level.set(i,i)
	# print(level.m_ZheighArray)

	control = CBedLevelComtrol(cmdList,testCB,level)
	control._file_manager=	TEST_file_manager()
	control.on_event('FileSelected', dict(origin='origin',path='path'))
	# control.on_event('path','origin',dict({u'estimatedPrintTime': 1433.505594528735, u'printingArea': {u'maxZ': 1.9, u'maxX': 185.087, u'maxY': 119.362, u'minX': 14.909, u'minY': 80.628, u'minZ': 0.3}, u'dimensions': {u'width': 170.178, u'depth': 38.733999999999995, u'height': 1.5999999999999999}, u'filament': {u'tool0': {u'volume': 0.0, u'length': 1459.9454600000004}}}))
	data =dict()
	control.on_update_front(data)
	print(data)
	control._width=30
	control._depth=10
	control.start(dict(feed_probe=40,feed_z=300,feed_xy=500,level_delta_z=0.5,grid=10))

	print(level.m_ZheighArray)
	control.cmdList.processResponce("ok")
	control.cmdList.processResponce("ok")
	control.cmdList.processResponce("ok")
	while True:
		control.cmdList.processResponce("X:216.00 Y:205.00 Z:0.00 E:0.00 Count A:34560 B:32800 Z:0")
		control.cmdList.processResponce("ok")
		if(control._state!="Init" and control._state!="Progress"):
			break
	print(level.m_ZheighArray)
	print(level.get_z_correction(0,0))
	print("test end")
