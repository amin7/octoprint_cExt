if __name__ == '__main__':
	from utils import *
else:
	from .utils import *
	
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
		status = dict(step=self.probe_area_step, count=self.bedLevel.get_count(), state=self._state)
		data['CBedLevelControl'] = status
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
					self._report(dict(state=self._state));
					self.cmdList.addGCode("M117 ProbeArea Done");
					if self._on_done:
						self._on_done(self.bedLevel)
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
class CMultyRun:
	def __init__(self, runner):
		self._runner=runner
		pass
	def run(self, cmd):
		if self._runner:
			for trans in self._runner:
				if trans:
					cmd = trans.run(cmd)
					pass
				pass
			pass
		return cmd
