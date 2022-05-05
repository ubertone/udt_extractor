from array import array
import numpy as np

from .peacock_uvp.apf04_gain import calc_gain, convert_code2dB_m, convert_code2dB, _convert_code2dB_trunc

class apf04_hardware ():
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