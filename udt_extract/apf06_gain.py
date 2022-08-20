#!/usr/bin/env python
# -*- coding: UTF_8 -*-

from math import pow

APF06_RECEPTION_CHAIN_CONSTANT_GAIN = 14.6 # dB
APF06_GAIN_CODE_RATIO = 1.5e-3  # dB/quantum 

APF06_CODE_MAX_APPLIED = 32767
APF06_CODE_MAX_USER = 65535
APF06_CODE_MIN_USER = -65535
APF06_CODE_MIN_APPLIED = 1280


def convert_dB_m2code(_gain_dB, _r_dvol):
    """Conversion of gain slope a1 (in dB) to code ca1.
        (difference with APF04 : 4 bits shift is not used)

    Args:
        _gain_dB(float): gain slope in dB/m
        _r_dvol(float): inter-volume size in m

    Returns:
        code (int)
    """
    code = int(round((_gain_dB * _r_dvol) / APF06_GAIN_CODE_RATIO, 1))
    code = _truncate(code, APF06_CODE_MAX_USER, APF06_CODE_MIN_USER)
    return code


def convert_code2dB_m(_code, _r_dvol):
    """Conversion of any code ca1 to gain slope a1 (in dB)
        (difference with APF04 : 4 bits shift is not used)

    Args:
        _code(int): gain code
        _r_dvol(float): inter-volume size in m

    Returns:
        gain slope in dB/m (float)
    """
    gain_dB = (APF06_GAIN_CODE_RATIO / _r_dvol) * _code
    return gain_dB


def convert_dB2code(_gain_dB):
    """Conversion of gain (in dB) to code.
        The code is truncated in the available range.

    Args:
        _gain_dB(float): gain intercept in dB

    Returns:
        gain code (int)
    """
    code = int(round((_gain_dB - APF06_RECEPTION_CHAIN_CONSTANT_GAIN) / APF06_GAIN_CODE_RATIO, 1))
    code = _truncate(code, APF06_CODE_MAX_APPLIED, APF06_CODE_MIN_USER)
    return code


def convert_code2dB(_code):
    """Conversion of any code to a theoretical gain (in dB)

    Args:
        _code(int): gain code

    Returns:
        gain intercept in dB (float)
    """
    gain_dB = (_code * APF06_GAIN_CODE_RATIO) + APF06_RECEPTION_CHAIN_CONSTANT_GAIN
    return gain_dB


def _convert_code2dB_trunc(_code):
    """Conversion of code to the effective (truncated) gain (in dB) applied in a cell
    
    Args :
        _code (int) : gain code

    Returns :
        gain in dB applied in a cell
    """
    _code = _truncate(_code, APF06_CODE_MAX_APPLIED, APF06_CODE_MIN_APPLIED)
    gain_dB = convert_code2dB(_code)
    return gain_dB


def calc_gain(_n_vol, _gain_ca0, _gain_ca1, _gain_max_ca0, _gain_max_ca1):
    """Compute the table of the gains in dB applied to each cell of the profile
     (difference with APF04 : 4 bits shift is not used)

    Args:
        _n_vol(int): number of cells in the profile
        _gain_ca0(int): code of the gain intercept
        _gain_ca1(int): code of the gain slope
        _gain_max_ca0(int): code of the blind zone gain limit intercept
        _gain_max_ca1(int): code of the blind zone gain limit slope

    Returns:
        list of gains in dB to apply to each cell of the profile
    
    """
    tab_gain = []
    i = 0
    while i <= (_n_vol - 1):
        G = _convert_code2dB_trunc(_gain_ca0 + i * _gain_ca1)
        G_max = _convert_code2dB_trunc(_gain_max_ca0 + i * _gain_max_ca1)
        if (G >= G_max):
            tab_gain.append(pow(10, G_max / 20.))
        else:
            tab_gain.append(pow(10, G / 20.))
        i = i + 1
    return tab_gain


def _truncate(value, limit_max, limit_min):
    """Troncate value with min/max limit

    Args:
        value: value to troncate
        limit_max: max limit
        limit_min: min limit

    Returns:
        the truncated value
    """
    return max(min(value, limit_max), limit_min)
