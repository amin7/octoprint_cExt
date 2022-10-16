if __name__ == '__main__':
	from utils import *
else:
	from .utils import *


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
	def __init__(self, plane, init_val=None):
		# round up
		self.m_grid = plane['grid']
		self.m_sizeX = roundToGrid(self.m_grid,plane['width'])
		self.m_sizeY = roundToGrid(self.m_grid,plane['depth'])
		self.m_ZheighArray = [[init_val for x in range(int(self.m_sizeY / self.m_grid  + 1))] for y in
			range(int(self.m_sizeX / self.m_grid  + 1))]
		pass

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
class CBedLevelAjust:
	def __init__(self, bedLevel):
		self._cur_X = 0
		self._cur_Y = 0
		self._cur_Z = 0
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


if __name__ == '__main__':
	from inspect import getframeinfo, stack
	print("test begin")
	level = CBedLevel(dict(width=9,depth=15, grid=5))
	test_isEQ(level.get_count(), 12)
	level = CBedLevel(dict(width=10,depth=11, grid=5))
	test_isEQ(level.get_count(), 12)
	level = CBedLevel(dict(width=10,depth=15, grid=5))
	test_isEQ(level.get_count(), 12)
	print("test end")