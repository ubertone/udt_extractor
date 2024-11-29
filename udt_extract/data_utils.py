#!/usr/bin/env python3
# -*- coding: UTF_8 -*-

import numpy as np
from numpy import asarray as ar

def conversion_scalar(scalar, key):
	"""Function that converts the scalar values from raw coded values to human readable and SI units.

	Args:
		scalars (list): 

	Returns:
		None
	"""
	if "temperature" in key:
		# convert temperature to Kelvin
		scalar = scalar + 273.15
	if ("pitch" in key) or ("roll" in key):
		# convert angles to rad
		scalar = scalar * np.pi/180.
	
	return float(scalar)
