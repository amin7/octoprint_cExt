# coding=utf-8
from __future__ import absolute_import
from collections import deque
import math

if __name__ == '__main__':
	from utils import *
else:
	from .utils import *

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


def roundToGrid(grid,val):
	return int(math.ceil(float(val) / grid) * grid)