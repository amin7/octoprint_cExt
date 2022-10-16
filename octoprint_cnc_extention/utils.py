# coding=utf-8
from __future__ import absolute_import
from collections import deque
import math
import re


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


def roundToGrid(grid,val):
	return int(math.ceil(float(val) / grid) * grid)

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

# --------------------------------------------------------------
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
# --------------------------------------------------------------
class COffsetXY:
	def __init__(self, offs_X, offs_Y):
		self._offs_X = offs_X
		self._offs_Y = offs_Y
		pass

	def status(self):
		return dict(x=self._offs_X,y=self._offs_Y)

	def run(self, cmd):
		g_parsed = gcode2dict(cmd)
		if g_parsed["cmd"] == "G0" or g_parsed["cmd"] == "G1":
			# add offet for absolute only
			if "X" in g_parsed:
				dest_x = g_parsed["X"] + self._offs_X
				pass
			if "Y" in g_parsed:
				dest_y = g_parsed["Y"] + self._offs_Y
				pass
			return dict2gcode(g_parsed)
		return cmd #nothing to change	    
	pass


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

def test_isEQ(v1, v2):
	if v1 != v2:
		caller = getframeinfo(stack()[1][0])
		print ("{file}:{line} ERROR {v1} != {v2}".format(file=caller.filename, line=caller.lineno, v1=v1, v2=v2))
		pass
	pass

def test_line(msg=None):
	caller = getframeinfo(stack()[1][0])
	print ("{file}:{line} {msg}".format(file=caller.filename, line=caller.lineno, msg=msg))
	pass


def testCB(response):
	print(response)
	pass


if __name__ == '__main__':
	from inspect import getframeinfo, stack
	print("test begin")

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

	test_isEQ(dict2gcode(gc), "G13 X1.0 Y10.2 Z23.0 F500.0")
	print("test done")