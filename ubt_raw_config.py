# -*- coding: UTF_8 -*-

# @copyright  this code is the property of Ubertone. 
# You may use this code for your personal, informational, non-commercial purpose. 
# You may not distribute, transmit, display, reproduce, publish, license, create derivative works from, transfer or sell any information, software, products or services based on this code.
# @author Stéphane Fischer
# @version 1.0
# @date 04 juillet 2016

from struct import calcsize, unpack

from peacock_uvp.apf04_config_hw import ConfigHw

from convert_type import translate_paramdict

def paramus_rawdict2ormdict(settings_dict):
	"""Function that converts a settings dict read from a raw file (webui2, UB-Lab P) to a formatted dict for data processing.

	Args:
		settings_dict (dict): original settings dict in raw.udt file

	Returns:
		paramus (dict): dict structure with keys the config int, with subkey the channel int and value the paramus dict
	"""
	#dict of config parameters of channel_id of config_id in this settings dict
	paramus = {}

	# keep order of configuration_order:
	for config_num in settings_dict["global"]["configuration_order"]:
		paramus[int(config_num[-1])] = {}
		temp_param = settings_dict["configs"][config_num]
		# clean subdicts parts:
		key2delete = []
		item2add = {}
		for key, elem in temp_param.items():
			if isinstance(elem,dict):
				print("type dict detected for key: %s"%key)
				for param_key, param_elem in elem.items():
					item2add[param_key] = param_elem
				key2delete.append(key)
		for key in key2delete:
			del temp_param[key]
		for key,elem in item2add.items():
			temp_param[key] = elem
		# translate for orm param names:

		temp_param = translate_paramdict(temp_param)
		# add global settings elements:
		temp_param["operator"] = settings_dict["global"]["operator"]
		temp_param["comments"] = settings_dict["global"]["comments"]
		temp_param["sound_speed"] = settings_dict["global"]["sound_speed"]["value"]


		# translate for orm with dict cleaner and with formated dict:
		paramus[int(config_num[-1])][int(temp_param["receiver"][2:])] = temp_param

	return paramus


def read_blind_ca_v2 (size, data):
	"""Reads blind_ca0 and 1 from config hw chunk from webui2 raw data

	Args:
	 	size (int): size of the data in the chunk
		data (bytes object): data in the chunk

	Returns:
	    blind_ca0 (float): intercept of limitation of gain in blind zone
	    blind_ca1 (float): slope of limitation of gain in blind zone
	"""
	head_size = 0
	blind_ca0, blind_ca1 = unpack('%dh'%2, data[head_size+size-2*calcsize('h'):head_size+size])
	return blind_ca0, blind_ca1

class ubt_raw_config ():
	def __init__(self, flag, size, data, f_sys):
		"""Function that initiates a ubt_raw_config objects allowing to extract the hardware configuration from a raw file (webui2, UB-Lab P).

		Args:
			flag (int): identification flag for data in the chunk
			size (int): size of the data in the chunk
			data (bytes object): data in the chunk
			f_sys (float): frequency of measurement system clock

		Returns:
			None
		"""
		if (size == 34):
			print("reading config driver")
			self.read_config_v2(size, data, f_sys)
		else:
			print("unknown config !")
			raise


	def read_config_v2 (self, size, data, f_sys):
		"""Function that creates a ConfigHw objects, extracting the hardware configuration from a raw file (webui2, UB-Lab P).

		Args:
			size (int): size of the data in the chunk
			data (bytes object): data in the chunk
			f_sys (float): frequency of measurement system clock

		Returns:
			None
		"""
		self.config_hw = ConfigHw(apf04_sys=f_sys)

		head_size = 0
		elem_size = size / calcsize('h')
		# à print en debug? print("elem_size = %d"%elem_size)
		self.config_hw.div_f0, self.config_hw.n_tir, self.config_hw.c_prf, self.config_hw.n_em, self.config_hw.n_vol, self.config_hw.c_vol1, self.config_hw.c_dvol, self.config_hw.gain_ca0, self.config_hw.gain_ca1, self.config_hw.tr, self.config_hw.phi_min, self.config_hw.method, vide1, vide2, self.config_hw.n_avg, self.config_hw.blind_ca0, self.config_hw.blind_ca1 = unpack('%dh'%elem_size, data[head_size:head_size+size])

		# tab_config_hw = []
		# for i in range(17*calcsize('h')):
		# 	elem_size = calcsize('h')
		# 	print "elem size: %d"%elem_size
		# 	print "head size: %d"%head_size
		# 	new_elem = unpack('h', data[head_size:head_size+elem_size])
		# 	tab_config_hw.append(new_elem)
		# 	head_size += elem_size
		# à print en debug? print("  config readed of size : %d" % head_size)

		# self.config_hw.load_from_tab(tab_config_hw)

		self.config_hw.print_config_hw()