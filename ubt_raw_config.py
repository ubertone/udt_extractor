# -*- coding: UTF_8 -*-

# @copyright  this code is the property of Ubertone. 
# You may use this code for your personal, informational, non-commercial purpose. 
# You may not distribute, transmit, display, reproduce, publish, license, create derivative works from, transfer or sell any information, software, products or services based on this code.
# @author Stéphane Fischer

from copy import deepcopy

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
				# for gain management
				#print("type dict detected for key: %s"%key)
				for param_key, param_elem in elem.items():
					item2add[param_key] = param_elem
				key2delete.append(key)
			#if isinstance(elem,list):
				# for receiver management
				#print("type list detected for key: %s"%key)
		for key in key2delete:
			del temp_param[key]
		for key,elem in item2add.items():
			temp_param[key] = elem

		if "tr_in" not in temp_param.keys():
			#print ("tr_in not defined. Monostatic mode, same as tr_out")
			temp_param["tr_in"] = temp_param["tr_out"]

		# translate for orm param names:
		temp_param = translate_paramdict(temp_param)

		# add global settings elements:
		temp_param["operator"] = settings_dict["global"]["operator"]
		temp_param["comments"] = settings_dict["global"]["comments"]
		temp_param["sound_speed"] = settings_dict["global"]["sound_speed"]["value"]

		# TODO si temp_param["receiver"] est une liste, il faut la balayer
		if isinstance(temp_param["receiver"],list):
			# TODO attention, en passant par un dictionnaire on va perdre l'ordre !!!
			for receiver in temp_param["receiver"]:
				#print ("process %s"%receiver) 
				# translate for orm with dict cleaner and with formated dict:
				paramus[int(config_num[-1])][int(receiver[2:])] = deepcopy(temp_param) # mandatory to avoid having multiple references on the same dict
				paramus[int(config_num[-1])][int(receiver[2:])]["receiver"] = receiver
		else:
			paramus[int(config_num[-1])][int(temp_param["receiver"][2:])] = temp_param

		#print(sorted(paramus[int(config_num[-1])].keys()))

	return paramus
	