

#<----------------- gcode send 
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
	response=""

	def processCommandList(self):
		if self.processingCommand==None:
			if self.cmdList:
				self.processingCommand=self.cmdList.popleft()
				self.sendGCode(self.processingCommand.command)	
				#send cmd


	def addGCode(self,command,callBack = None):
		commands = filter(None, command.split('\n')) #ignore emply
		commlen=len(commands)
		for i in range(commlen):
			cmd=self.CCommand(commands[i]);
			if(i==commlen-1):
				cmd.callBack=callBack
			self.cmdList.append(cmd)
		self.processCommandList()

	def processResponce(self,response):
		if self.processingCommand!=None:
			self.response+=response;
			if(response.startswith('ok')):
				if(self.processingCommand.callBack!=None):
					self.processingCommand.callBack(self.response)
				self.processingCommand=None
				self.response=""
				self.processCommandList()
			else:
				self.response+='\n'

#<----------------- gcode send 

def testCB(response):
	print(response)	

def sendGCode(response):
	print("send :"+response)

if __name__ == '__main__':
	# test1.py executed as script
	# do something
	test=CCmdList(sendGCode)
	test.addGCode("G10\n\nF20",testCB)
	print(test.cmdList)
	test.processResponce("ok")
	print(test.cmdList)
	test.processResponce("ok")
	print(test.cmdList)
