#!/usr/bin/env python3

# @copyright  this code is the property of Ubertone. 
# You may use this code for your personal, informational, non-commercial purpose. 
# You may not distribute, transmit, display, reproduce, publish, license, create derivative works from, transfer or sell any information, software, products or services based on this code.
# @author Stéphane Fischer

from struct import calcsize, unpack
from array import *
import numpy as np
from numpy import asarray as ar

from peacock_uvp.apf_timestamp import decode_timestamp
from peacock_uvp.apf04_gain import calc_gain, convert_code2dB_m, convert_code2dB, _convert_code2dB_trunc

from convert_type import translate_key
from date_parser import date_parse

class ubt_raw_data () :
	def __init__ (self, param_us_dicts, blind_ca0, blind_ca1):
		"""Function that initiates z ubt_raw_data object which contains the data read in a raw.udt file.

		Args:
		    param_us_dicts (dict): dicts of the param_us for each config and each receiving channel
		    blind_ca0 (float): intercept of limitation of gain in blind zone
		    blind_ca1 (float): slope of limitation of gain in blind zone

		Returns:
		    None
		"""
		# liste des dictionnaires standardisés des données non US (model Measure)
		self.data_dicts = {}
		# dict, ordonné par num_config, channel_id, de listes des dictionnaires standardisés des données US (model MeasureUs)
		self.data_us_dicts = {}
		self.param_us_dicts = param_us_dicts
		self.blind_ca0 = blind_ca0
		self.blind_ca1 = blind_ca1
		for config in self.param_us_dicts.keys():
			self.data_us_dicts[config] = {}
			channel = list(self.param_us_dicts[config].keys())[0]
			self.data_us_dicts[config][channel] = {}
			for datatype in ["echo_avg_profile", "echo_sat_profile", "velocity_avg_profile", "snr_doppler_avg_profile", "velocity_std_profile"]:
				self.data_us_dicts[config][channel][datatype] = {"time":[], "data":[]}
		self.current_config = None
		self.current_channel = None

	def read_line (self, size, data) :
		"""Utilise une frame pour récupérer un profil voulu (pour fichiers UDT005)
		une ligne de profil dans raw UDT005 contient: (ref&0x000007FF)<<4 or int(config_key) puis le raw profile
		le raw profile contient un header puis le profil codé
		ce header contient des scalaires qu'il faut aussi enregistrer
		Nous rangeons les données us dans un dict data_us_dicts hiérarchiquement par config, par channel récepteur, par datatype.
		Les données non us sont rangées dans un dict data_dicts par datatype.
		Chaque donnée a ses valeurs listées à la clé "data" et ses timestamps correspondants listés à la clé "time".
		Il y a donc forte potentielle duplication de la donnée "time", mais cela permet une plus grande liberté dans l'utilisation des données ensuite
		et couvre le cas où on aurait des données non systématiquement enregristrées (désinchronisées) lors d'un record.
		Exemple: pour des données d'APF02, on a des données de profils instantanés, mais le gain auto n'est re-calculé qu'à chaque bloc.

        Args:
            _size (int) : la taille du bloc
            _data : le bloc de données binaire

        Returns:
            None
        """

	##################################################
	#	header reading: timestamp and config reference
	##################################################
		head_size = calcsize('hhhh')
		ref = unpack('h', data[0:2])
		# ref_config : la référence des settings (numéro unique)
		# print("ref %s" % (ref >> 4))
		# self.current_config : le numéro de la configuration utilisée (1 à 3)
		self.current_config = int(ref[0] & 0x0000000F) + 1
		self.current_channel = list(self.param_us_dicts[self.current_config].keys())[0]

		# print("num config %s" % self.current_config)
		if self.current_config not in self.data_us_dicts.keys():
			raise Exception('chunk', "unexpected number of configurations (%d)" % self.current_config)

		#print(convert_packed_timestamp(nsec_pF, nsec_pf, msec))
		#print(convert_packed_timestamp(nsec_pF, nsec_pf, msec).strftime("%Y-%m-%dT%H:%M:%S.%f"))
		dt_timestamp, _ = decode_timestamp(data[2:head_size])
		time = date_parse(dt_timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"))
		#print("time", type(time))
		#print("time", time)

		# A few acoustic parameters which are needed for the following calculations
		n_vol = self.param_us_dicts[self.current_config][self.current_channel]["n_cell"]
		c_prf = self.param_us_dicts[self.current_config][self.current_channel]["f0"] / \
				self.param_us_dicts[self.current_config][self.current_channel]["prf"]
		n_avg = self.param_us_dicts[self.current_config][self.current_channel]["n_avg"]
		r_dvol = self.param_us_dicts[self.current_config][self.current_channel]['r_dcell']
		r_vol1 = self.param_us_dicts[self.current_config][self.current_channel]['r_cell1']

	###################
	#	scalars reading
	###################
		scalars_size = calcsize('hhhhhhhh')
		scalars_us_dict = {}
		scalars_dict = {}
		scalars_dict['pitch'], scalars_dict['roll'], scalars_dict['temp'], sound_speed, scalars_us_dict['gain_ca0'], scalars_us_dict['gain_ca1'], scalars_us_dict['noise_g_max'], scalars_us_dict['noise_g_mid'] = unpack('hhhhhhhh', data[head_size:head_size+scalars_size])

		if (size - (head_size+scalars_size)) / 4 / 2 != n_vol:
			raise Exception('volume number', "expected %d volumes, but profile data contains %d" % (
				n_vol, ((size - (head_size + scalars_size)) / 4 / 2)))


	###################
	#	vectors reading
	###################
		vectors_dict = {
			"velocity" : [],
			"amplitude" : [],
			"snr" : [],
			"std" : []
		}

		tab_size = calcsize('h')
		offset = head_size+scalars_size
		unpacked_data = ar(unpack('%dh'%(4*n_vol), data[offset:offset + 4*n_vol*tab_size]))
		#print(unpacked_data)
		vectors_dict['velocity'] = unpacked_data[0::4]
		vectors_dict['std'] = unpacked_data[1::4]
		vectors_dict['amplitude'] = unpacked_data[2::4]
		vectors_dict['snr'] = unpacked_data[3::4]

		# print(vectors_dict)

	##################################
	#	conversion des valeurs codées:
	##################################
		# Note: il faut convertir les scalaires après pour avoir les gains tels que pour la conversion du profil d'echo
		self.conversion_profile(vectors_dict, sound_speed, n_vol, n_avg, c_prf, scalars_us_dict['gain_ca0'], scalars_us_dict['gain_ca1'], self.blind_ca0[self.current_config-1], self.blind_ca1[self.current_config-1])
		self.conversion_scalar(scalars_dict)
		self.conversion_us_scalar(scalars_us_dict, n_avg, r_dvol, r_vol1)

	###################################################################################################
	# rangement dans la liste de dictionnaires de données US (ici tous les profils sont des données US)
	###################################################################################################
		for datatype in ["echo_avg_profile", "echo_sat_profile", "velocity_avg_profile", "snr_doppler_avg_profile",
						 "velocity_std_profile"]:
			self.data_us_dicts[self.current_config][self.current_channel][datatype]["time"].append(time)
		self.data_us_dicts[self.current_config][self.current_channel]["echo_avg_profile"]["data"].append(vectors_dict['amplitude'])
		self.data_us_dicts[self.current_config][self.current_channel]["echo_sat_profile"]["data"].append(vectors_dict['sat'])
		self.data_us_dicts[self.current_config][self.current_channel]["velocity_avg_profile"]["data"].append(vectors_dict['velocity'])
		self.data_us_dicts[self.current_config][self.current_channel]["snr_doppler_avg_profile"]["data"].append(vectors_dict['snr'])
		self.data_us_dicts[self.current_config][self.current_channel]["velocity_std_profile"]["data"].append(vectors_dict['std'])

		# traduction des noms des types de données US:
		for key, value in scalars_us_dict.items():
			translated_key = translate_key(key)
			# gestion des scalaires qui sont des paramètres us variables (auto)
			if translated_key == None:
				translated_key = translate_key(key, _type="param_var")
				if translated_key:
					translated_key = translated_key+"_param"
			if translated_key:
				if translated_key not in self.data_us_dicts[self.current_config][self.current_channel].keys():
					self.data_us_dicts[self.current_config][self.current_channel][translated_key] = {"time":[], "data":[]}
				self.data_us_dicts[self.current_config][self.current_channel][translated_key]["data"].append(value)
				self.data_us_dicts[self.current_config][self.current_channel][translated_key]["time"].append(time)

		# traduction des noms des types de données non US:
		for key, value in scalars_dict.items():
			translated_key = translate_key(key)
			if translated_key:
				if translated_key not in self.data_dicts.keys():
					self.data_dicts[translated_key] = {"time":[], "data":[]}
				self.data_dicts[translated_key]["data"].append(value)
				self.data_dicts[translated_key]["time"].append(time)


	def conversion_profile(self, vectors_dict, sound_speed, n_vol, n_avg, c_prf, gain_ca0, gain_ca1, blind_ca0, blind_ca1):
		"""Function that converts the US profiles values from raw coded values to human readable and SI units.

		Args:
		    vectors_dict (dict): dict of unique vectors keyed by datatype
		    sound_speed (float): sound speed used for this measurement
		    n_vol, n_avg, c_prf, gain_ca0, gain_ca1 (floats): parameters for the ongoing param_us (one config, one channel): number of cells, of measures per block, coded PRF, gain intercept and gain slope.
		    blind_ca0, blind_ca1 (floats): intercept and slope of limitation of gain in blind zone

		Returns:
		    None
		"""
		#APF04 or APF04S
		self.sat = array('f')
		self.ny_jump = array('f')

		v_ref = 1.25
		fact_code2velocity = sound_speed / (c_prf * 65535.)
		# print("factor code to velocity %f"%fact_code2velocity)
		tab_gain = calc_gain(n_vol, gain_ca0, gain_ca1, blind_ca0, blind_ca1)

		# Nypquist jump when raw velocity standard deviation <0
		self.ny_jump = vectors_dict['std'] < 0

		# conversion raw velocity standard deviation and raw velocity
		vectors_dict['std'] = (np.absolute(vectors_dict['std'])-1)*fact_code2velocity
		vectors_dict['velocity'] = vectors_dict['velocity']*fact_code2velocity

		# Saturation when raw echo amplitude <0
		vectors_dict['sat'] = vectors_dict['amplitude'] < 0

		# conversion of raw echo amplitude and gain taken into account
		vectors_dict['amplitude'] = np.absolute(vectors_dict['amplitude']) * ((v_ref*2)/4096) / np.sqrt(n_avg) / tab_gain

		# conversion raw snr
		vectors_dict['snr'] = vectors_dict['snr'] / 10.

	def conversion_scalar(self, scalars_dict):
		"""Function that converts the scalar values from raw coded values to human readable and SI units.

		Args:
		    scalars_dict (dict): dict of scalars keyed by datatype

		Returns:
			None
		"""
		# convert temperature to Kelvin
		scalars_dict["temp"] += 273.15

		# convert angles to rad
		scalars_dict['pitch'] *= np.pi/180.
		scalars_dict['roll'] *= np.pi/180.

	def conversion_us_scalar(self, scalars_dict, n_avg, r_dvol, r_vol1):
		"""Function that converts the scalar US values from raw coded values to human readable and SI units.

		Args:
		    scalars_dict (dict): dict of scalars US keyed by datatype
		    n_avg, r_dvol, r_vol1 (floats): parameters for the ongoing param_us (one config, one channel): number of measurements per block, intercell distance and first cell position.

		Returns:
			None
		"""
		# convert coded gain to dB and dB/m
		scalars_dict["a1"] = convert_code2dB_m(scalars_dict["gain_ca1"], r_dvol)
		del scalars_dict["gain_ca1"]
		scalars_dict["a0"] = convert_code2dB(scalars_dict["gain_ca0"])-scalars_dict["a1"]*r_vol1
		del scalars_dict["gain_ca0"]

		# convert coded noise values to V
		v_ref = 1.25
		gain = pow(10, ((_convert_code2dB_trunc(1241)) / 20.)) # gain max
		scalars_dict["noise_g_high"] = scalars_dict["noise_g_max"] * ((v_ref*2)/4096) / np.sqrt(n_avg) / gain
		del scalars_dict["noise_g_max"]

		gain = pow(10, ((_convert_code2dB_trunc(993)) / 20.)) # gain max - 10dB
		scalars_dict["noise_g_low"] = scalars_dict["noise_g_mid"] * ((v_ref*2)/4096) / np.sqrt(n_avg) / gain
		del scalars_dict["noise_g_mid"]