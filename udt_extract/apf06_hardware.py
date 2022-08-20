from array import array
import numpy as np

from .apf06_gain import calc_gain, convert_code2dB_m, convert_code2dB, APF06_CODE_MAX_APPLIED

class apf06_hardware ():
    def conversion_profile(self, vectors_dict, sound_speed, n_vol, n_avg, c_prf, gain_ca0, gain_ca1, blind_ca0, blind_ca1):
        """Function that converts the US profiles values from raw coded values to human readable and SI units.

        Args:
            vectors_dict (dict): dict of unique vectors keyed by datatype
            sound_speed (float): sound speed used for this measurement
            n_vol, n_avg, c_prf, gain_ca0, gain_ca1 (floats): parameters for the ongoing param_us (one config, one channel): number of cells, of measures per block, coded PRF, gain intercept and gain slope.
            not used yet : blind_ca0, blind_ca1 (floats): intercept and slope of limitation of gain in blind zone

        Returns:
            None
        """
        #APF04 or APF04S
        self.sat = array('f')
        self.ny_jump = array('f')

        fact_code2velocity = sound_speed / (c_prf * 65535.)
        # print("factor code to velocity %f"%fact_code2velocity)

        tab_gain = calc_gain(n_vol, gain_ca0, gain_ca1, gain_ca0, gain_ca1) #blind_ca0, blind_ca1)

        vectors_dict['velocity'] = vectors_dict['velocity']*fact_code2velocity

        # Saturation when raw echo amplitude <0
        vectors_dict['sat'] = vectors_dict['amplitude'] < 0

        # conversion of raw echo amplitude and gain taken into account
        vectors_dict['amplitude'] = np.absolute(vectors_dict['amplitude']) * (2./4096) / tab_gain

        # conversion raw snr
        vectors_dict['snr'] = vectors_dict['snr'] / 10.

    
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
        # not implemented yet
        scalars_dict["noise_g_high"] = 0
        del scalars_dict["noise_g_max"]
        scalars_dict["noise_g_low"] = 0
        del scalars_dict["noise_g_mid"]