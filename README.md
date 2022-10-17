# OctoPrint-Cext

cnc Extention for Octoprint.
do bed leveling for PCB etching area 
works with gcodes G38.2/G38.4 marlin FW
## Setup

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

    https://github.com/you/octoprint_cExt/archive/master.zip

## Configuration
CNC part is speds for ajustment 0

Probe Area praramenter for bed leveling

#operation
!! do not forget to attach probing wires to Engraver
A) if have only one etch file
1. Open CNC plugin Tab
2. Select file for etching
3. set XY initail point
4. Set Zero (buttont Z-, is using probe)
5. Do probe area (or skip it if it flat)
6. Start engrave by press Engrave button

B) if you have mill, drill, etch files
1. Open CNC plugin Tab
2. Select file mill file (it biggest size, this file will be used as plane)
3. set XY initail point
4. Set Zero (buttont Z-, is using probe)
5. Do probe area (it will be used for all files that will be runed after)
6. Select file for etch 
7. engrave it
8. select file for drill
9. drill
10. select file for mill
11. mill
....

