#!/usr/bin/env python3

# @copyright  this code is the property of Ubertone. 
# You may use this code for your personal, informational, non-commercial purpose. 
# You may not distribute, transmit, display, reproduce, publish, license, create derivative works from, transfer or sell any information, software, products or services based on this code.
# @author Stéphane Fischer

#from ctypes import sizeof
from struct import calcsize, unpack
import numpy as np
from numpy import asarray as ar

from peacock_uvp.apf_timestamp import decode_timestamp

from convert_type import translate_key
from date_parser import date_parse
from ubt_raw_config import paramus_rawdict2ormdict

class ubt_raw_data () :
    def __init__ (self, _const):
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

                        
        self.board = "apf"+ _const["hardware"]["board_version"].lower().split('apf')[1]
        print("initiating ubt_raw_data for board %s" %self.board)
        assert (self.board in ["apf04", "apf06"])
        if self.board == "apf04" :
            from apf04_hardware import apf04_hardware
            self.hardware = apf04_hardware()
        elif self.board == "apf06" :
            from apf06_hardware import apf06_hardware
            self.hardware = apf06_hardware()

        self.current_config = None
        self.current_channel = None

    def set_config (self, _settings):

        param_us_dicts = paramus_rawdict2ormdict(_settings)
        self.param_us_dicts = param_us_dicts

        # list of blind zone gain parameters :
        self.blind_ca0 = []
        self.blind_ca1 = []

        for config in self.param_us_dicts.keys():
            self.data_us_dicts[config] = {}

            for channel in self.param_us_dicts[config].keys():
                self.data_us_dicts[config][channel] = {}
                if self.board == "apf06" : # test pas idéal, mais fonctionnel dans l'état actuel
                    for datatype in ["echo_profile", "saturation_profile", "velocity_profile", "snr_doppler_profile"]:
                        self.data_us_dicts[config][channel][datatype] = {"time": [], "data": []}
                else :
                    for datatype in ["echo_avg_profile", "saturation_avg_profile", "velocity_avg_profile", "snr_doppler_avg_profile", "velocity_std_profile"]:
                        self.data_us_dicts[config][channel][datatype] = {"time":[], "data":[]}


    def set_confighw (self, _size, _data):
        blind_ca0, blind_ca1 = unpack('%dh'%2, _data[_size-2*calcsize('h'):_size])
        
        # les config HW (toujours écrits dans l'ordre dans le raw)
        # we use a list with config id (0..N-1) as index
        self.blind_ca0.append(blind_ca0)
        self.blind_ca1.append(blind_ca1)

    def read_line (self, size, data, _inst=False) :
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
            timestamp
        """

        if _inst :
            data_per_cell = 3
        else :
            data_per_cell = 4
    ##################################################
    #	header reading: timestamp and config reference
    ##################################################
        head_size = calcsize('hhhh')
        ref = unpack('h', data[0:2])
        # ref_config : la référence des settings (numéro unique)
        # print("ref %s" % (ref >> 4))
        # self.current_config : le numéro de la configuration utilisée (1 à 3)
        self.current_config = int(ref[0] & 0x0000000F) + 1
        # get the first channel :
        self.current_channel = list(self.param_us_dicts[self.current_config].keys())[0]
        #print (self.param_us_dicts[self.current_config].keys())

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
        nb_rx = len(self.param_us_dicts[self.current_config])

        #print ("n_vol = %d ; nb_rx = %d"%(n_vol, nb_rx))

    ###################
    #	scalars reading
    ###################
        scalars_size = calcsize('hhhhhh')
        scalars_us_dict = {}
        scalars_dict = {}
        scalars_dict['pitch'], scalars_dict['roll'], scalars_dict['temp'], sound_speed, scalars_us_dict['gain_ca0'], scalars_us_dict['gain_ca1'] = unpack('hhhhhh', data[head_size:head_size+scalars_size])


        for _ in range(nb_rx):
            # TODO attention il faudra traiter individuellement le bruit de chaque ligne
            scalars_us_dict['noise_g_max'], scalars_us_dict['noise_g_mid'] = unpack("hh", data[head_size+scalars_size:head_size+scalars_size+calcsize('hh')])
            scalars_size += calcsize('hh')

        if (size - (head_size+scalars_size)) / (data_per_cell * 2) != n_vol * nb_rx:
            raise Exception('volume number', "expected %d volumes, but profile data contains %d" % (
                n_vol, ((size - (head_size + scalars_size)) / (data_per_cell * 2 * nb_rx))))


    ###################
    #	vectors reading
    ###################

        vectors_dict = {}

        offset = head_size+scalars_size
        unpacked_data = ar(unpack('%dh'%(data_per_cell*n_vol*nb_rx), data[offset:offset + data_per_cell*n_vol*nb_rx*calcsize('h')]))

        channels = sorted(self.param_us_dicts[self.current_config].keys())
        for channel_id in range(len(channels)):
            #print ("processing %d"%channel_id)
            self.current_channel = channels[channel_id]
            # [offset + i*data_per_cell*nb_tr_rx + meas_data.current_receiver*data_per_cell + velocity_rank ]);
            
            if _inst :
                vectors_dict['amplitude'] = unpacked_data[0+3*channel_id::3*nb_rx]
                vectors_dict['velocity'] = unpacked_data[1+3*channel_id::3*nb_rx]
                vectors_dict['snr'] = unpacked_data[2+3*channel_id::3*nb_rx]
            else :
                #print(unpacked_data)
                # TODO on pourrait utiliser directement les nom destinés à l'ORM (ça pourrait simplifier la boucle sur les datatype)
                vectors_dict['velocity'] = unpacked_data[0+4*channel_id::4*nb_rx]
                vectors_dict['std'] = unpacked_data[1+4*channel_id::4*nb_rx]
                vectors_dict['amplitude'] = unpacked_data[2+4*channel_id::4*nb_rx]
                vectors_dict['snr'] = unpacked_data[3+4*channel_id::4*nb_rx]

            # print(vectors_dict)

        ##################################
        #	conversion des valeurs codées:
        ##################################
            
                # Note: il faut convertir les scalaires après pour avoir les gains tels que pour la conversion du profil d'echo
            self.hardware.conversion_profile(vectors_dict, sound_speed, n_vol, n_avg, c_prf, scalars_us_dict['gain_ca0'], scalars_us_dict['gain_ca1'], self.blind_ca0[self.current_config-1], self.blind_ca1[self.current_config-1])
           # elif self.board == "apf06" :
           #     self.conversion_profile_apf06(vectors_dict, sound_speed, n_vol, c_prf, scalars_us_dict['gain_ca0'], scalars_us_dict['gain_ca1'])

        ###################################################################################################
        # rangement dans la liste de dictionnaires de données US (ici tous les profils sont des données US)
        ###################################################################################################
            if _inst :
                for datatype in ["echo_profile", "saturation_profile", "velocity_profile", "snr_doppler_profile"]:
                    self.data_us_dicts[self.current_config][self.current_channel][datatype]["time"].append(time)

                self.data_us_dicts[self.current_config][self.current_channel]["echo_profile"]["data"].append(vectors_dict['amplitude'])
                self.data_us_dicts[self.current_config][self.current_channel]["saturation_profile"]["data"].append(vectors_dict['sat'])
                self.data_us_dicts[self.current_config][self.current_channel]["velocity_profile"]["data"].append(vectors_dict['velocity'])
                self.data_us_dicts[self.current_config][self.current_channel]["snr_doppler_profile"]["data"].append(vectors_dict['snr'])
            else:
                for datatype in ["echo_avg_profile", "saturation_avg_profile", "velocity_avg_profile", "snr_doppler_avg_profile",
                                "velocity_std_profile"]:
                    self.data_us_dicts[self.current_config][self.current_channel][datatype]["time"].append(time)

                self.data_us_dicts[self.current_config][self.current_channel]["echo_avg_profile"]["data"].append(vectors_dict['amplitude'])
                self.data_us_dicts[self.current_config][self.current_channel]["saturation_avg_profile"]["data"].append(vectors_dict['sat'])
                self.data_us_dicts[self.current_config][self.current_channel]["velocity_avg_profile"]["data"].append(vectors_dict['velocity'])
                self.data_us_dicts[self.current_config][self.current_channel]["snr_doppler_avg_profile"]["data"].append(vectors_dict['snr'])
                self.data_us_dicts[self.current_config][self.current_channel]["velocity_std_profile"]["data"].append(vectors_dict['std'])


        # get the first channel again:
        self.current_channel = list(self.param_us_dicts[self.current_config].keys())[0]
        
        self.hardware.conversion_us_scalar(scalars_us_dict, n_avg, r_dvol, r_vol1)
        # traduction des noms des types de données US:
        # TODO note : commun à tous les channels
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

        self.conversion_scalar(scalars_dict)
        # traduction des noms des types de données non US:
        for key, value in scalars_dict.items():
            translated_key = translate_key(key)
            if translated_key:
                if translated_key not in self.data_dicts.keys():
                    self.data_dicts[translated_key] = {"time":[], "data":[]}
                self.data_dicts[translated_key]["data"].append(value)
                self.data_dicts[translated_key]["time"].append(time)

        return time


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