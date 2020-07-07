
import re

from collections import deque

GCODE_ABSOLUTE_POSITIONING ='G90'
GCODE_RELATIVEPOSITIONING ='G91'
GCODE_PROBE_UP="G38.4 F{feed} Z{dist}"
GCODE_PROBE_DOWN="G38.2 F{feed} Z{dist}"
GCODE_AUTO_HOME="G28 {axis}"
GCODE_MOVE_XY="G0 F{feed} X{pos_x} Y{pos_y}"
GCODE_MOVE_Z="G0 F{feed} Z{dist}"
GCODE_SET_POS_000="G92 X0 Y0 Z0"

#<----------------- gcode send
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

#<----------------- gcode send

def testCB(response):
    print(response)

def sendGCode(response):
    print("send :"+response)

#<--------------------------
import math
class CBedLevel:
    m_sizeX=float('nan')
    m_sizeY=float('nan')
    m_grid=float('nan')
    m_ZheighArray=None
    #protected
    def cell_index(self,coord,max):
        if (coord <= 0):
            return 0;
        if (coord >= max):
            return max / self.m_grid;
        return coord / self.m_grid;

    #public
    def init(self,width,depth,grid):
        # round up
        self.m_sizeX=int((width+grid)/grid)*grid
        self.m_sizeY=int((depth+grid)/grid)*grid
        self.m_grid=grid
        self.m_ZheighArray = [[float('nan') for x in range(int(self.m_sizeY/grid+1))] for y in range(int(self.m_sizeX/grid+1))]

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

    def set(self, index, z_height):
        self.m_ZheighArray[self.get_i_x(index)][self.get_i_y(index)]=z_height;

    def get_count(self):
        return int((self.m_sizeX/self.m_grid+1)*(self.m_sizeY/self.m_grid+1))


class CBedLevelComtrol:
    def __init__(self,cmdList,progress_cb,bedLevel):
        self.cmdList=cmdList
        self.bedLevel=bedLevel
        self.progress_cb=progress_cb
        self.on_onit()
        pass

    def on_onit(self):
        self._path=None
        self._origin=None
        self._width=None
        self._depth=None
        self._min_x=None
        self._min_y=None
        self.probe_area_step=None
        self.probe_area_state=None
        pass

    def on_file_selected(self,path,origin,analysis=None):
        self._path=path
        self._origin=origin
        if analysis :
            self._width=analysis['dimensions']['width']
            self._depth=analysis['dimensions']['depth']
            self._min_x=analysis['printingArea']['minX']
            self._min_y=analysis['printingArea']['minY']
        pass

    def on_update_front(self,data):
        data['file_selected_path']=self._path
        data['file_selected_width']=self._width
        data['file_selected_depth']=self._depth
        pass

    def on_progress(self):
        data=dict()
        data['probe_area_step']=self.probe_area_step
        data['probe_area_count']=self.bedLevel.get_count()
        data['probe_area_state']=self.probe_area_state
        self.progress_cb(data)
        pass

    def on_stop(self):
        pass

    def on_error(self,err):
        self.probe_area_state=err
        self.on_progress()
        self.cmdList.clearCommandList()
        self.cmdList.addGCode([GCODE_RELATIVEPOSITIONING, GCODE_MOVE_Z.format(feed=self.feed_z,dist=self.level_delta_z)])
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
                    self.cmdList.addGCode(GCODE_SET_POS_000)
                self.bedLevel.set(self.probe_area_step,zpos);
                self.probe_area_step+=1;
                if(self.probe_area_step<self.bedLevel.get_count()):
                    self.probe_area_state="Progress"
                    self.make_probe()
                else:
                    self.probe_area_state="Done"
                self.on_progress()
                return
            pass
        self.on_error("unproper answer")
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

    def on_probe_area(self,grid,feed_probe,feed_z,feed_xy,level_delta_z):
        self.probe_area_step=0
        self.feed_probe=feed_probe
        self.feed_z=feed_z
        self.feed_xy=feed_xy
        self.level_delta_z=level_delta_z
        self.bedLevel.init(self._width,self._depth,grid)
        self.probe_area_state="Init"
        self.on_progress()
        #preinit
        self.cmdList.addGCode([GCODE_SET_POS_000,GCODE_RELATIVEPOSITIONING,GCODE_MOVE_Z.format(feed=self.feed_z,dist=self.level_delta_z)])
        self.make_probe()
        pass

class CProbeComtrol:

    def __init__(self,cmdList,progress_cb):
        self.cmdList=cmdList
        self.progress_cb=progress_cb
        self.on_onit()
        pass

    def cb_stop_on_error(self,response):
        for line in response:
            if line.startswith("Error:Failed to reach target"):
                self.cmdList.clearCommandList()
                progress_cb(dict(probe_state='Failed'))
                pass
        pass

    def cb_echo(self,response):
        for line in response:
            match=re.match("^X:(?P<val_x>-?\d+\.\d+)\sY:(?P<val_y>-?\d+\.\d+)\sZ:(?P<val_z>-?\d+\.\d+)\sE:-?\d+\.\d+",line)
            if(match):
                result="Probe Done Z:{zpos}".format(zpos=match.group('val_z'));
                progress_cb(dict(probe_state=result))
                self.cmdList.addGCode("M117 "+result);
                return
        progress_cb(dict(probe_state='unproper answer'))
        pass

    def start(self,data):
        self._plugin_manager.send_plugin_message(self._identifier, dict(probe_state='probing'))
        progress_cb(dict(probe_state='probing'))
        self.cmdList.addGCode(GCODE_RELATIVEPOSITIONING)
        #fast probe
        self.cmdList.addGCode(GCODE_PROBE_DOWN.format(feed=data["feed"],dist=-1*data["distanse"]),self.cb_stop_on_error)
        #show pos
        self.cmdList.addGCode("M114",self.cb_echo)
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

    control=CBedLevelComtrol(cmdList,testCB,level)
    control.on_file_selected('path','origin')
    control.on_file_selected('path','origin',dict({u'estimatedPrintTime': 1433.505594528735, u'printingArea': {u'maxZ': 1.9, u'maxX': 185.087, u'maxY': 119.362, u'minX': 14.909, u'minY': 80.628, u'minZ': 0.3}, u'dimensions': {u'width': 170.178, u'depth': 38.733999999999995, u'height': 1.5999999999999999}, u'filament': {u'tool0': {u'volume': 0.0, u'length': 1459.9454600000004}}}))
    data =dict()
    control.on_update_front(data)
    print(data)
    control.on_probe_area(20,40,300,500,0.5)
    print(level.m_ZheighArray)
    control.cmdList.processResponce("ok")
    control.cmdList.processResponce("ok")
    control.cmdList.processResponce("ok")
    while True:
        control.cmdList.processResponce("ok")
        control.cmdList.processResponce("ok")
        control.cmdList.processResponce("ok")
        control.cmdList.processResponce("ok")
        control.cmdList.processResponce("X:216.00 Y:205.00 Z:0.00 E:0.00 Count A:34560 B:32800 Z:0")
        control.cmdList.processResponce("ok")
        control.cmdList.processResponce("ok")
        if control.probe_area_step==1:
            control.cmdList.processResponce("ok")
        if(control.probe_area_state!="Progress"):
            break
    print(level.m_ZheighArray)
    print("test end")
