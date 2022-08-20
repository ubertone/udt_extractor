# -*- coding: UTF_8 -*-

# @copyright  this code is the property of Ubertone.
# You may use this code for your personal, informational, non-commercial purpose.
# You may not distribute, transmit, display, reproduce, publish, license, create derivative works from, transfer or sell any information, software, products or services based on this code.
# @author Stéphane Fischer

import json
from datetime import datetime  # pour time count

from .ubt_raw_file import ubt_raw_file
from .ubt_raw_data import ubt_raw_data
from .ubt_raw_flag import *


def raw_extract(_raw_file):
    """
        This method will extract data from the raw.udt file and convert it to dicts which are easy to go through and to import in the DB.

        Parameters
        ----------
        _raw_file : string
                path to .udt file

        Returns
        -------
    device_name : string
    time_begin : datetime
    time_end : datetime
    data_us_dicts : list of dicts
        data, us related, with param_us associated
    param_us_dicts : list of dicts
        param_us for us related data
    data_dicts : list of dicts
        data not us related, with no param_us associated
    """

    fileraw = ubt_raw_file(_raw_file)


    profile_id = 0
    try:
        while 1:
            flag, size, data = fileraw.read_chunk()

            # Pour raw UDT005 (ie. UB-Lab P, UB-SediFlow, UB-Lab 3C) on peut 
            # rencontrer 4 flags: const, settings json, configs (HW), profils
            if flag == CONST_TAG:
                try:
                    const_dict = json.loads(data.decode("utf-8"))
                except:
                    const_dict = json.loads(
                        data.decode("utf-8")
                        .replace("'", '"')
                        .replace("True", "true")
                        .replace("False", "false")
                    )
                print("const: %s" % const_dict)

                ubt_data = ubt_raw_data( const_dict )


            if flag == SETTINGS_JSON_TAG:
                try:
                    settings_dict = json.loads(data.decode("utf-8"))
                except:
                    settings_dict = json.loads(
                        data.decode("utf-8")
                        .replace("'", '"')
                        .replace("True", "true")
                        .replace("False", "false")
                    )
                print("settings: %s" % settings_dict)

                ubt_data.set_config(settings_dict)


            if flag == CONFIG_TAG:
                # what is needed from here and which is not in param_us_dict is only blind_ca0 and blind_ca1
                # note: this is not useful on APF06, but could be used for double check
                ubt_data.set_confighw(size, data)


            if flag == PROFILE_TAG or flag == PROFILE_INST_TAG:
                timestamp = ubt_data.read_line(size, data, flag==PROFILE_INST_TAG)
                profile_id += 1

                # get the first timestamp of udt file for time_begin definition of the run:
                if profile_id == 1:
                    time_begin = timestamp

    except KeyboardInterrupt:
        print("read interrupted by user")
    except EOFError:
        print("End of file")
    except:
        print("Error")
        raise

    #print("%d profiles read" % profile_id)
    # last timestamp of udt file for time_end definition of run:
    # based on the last profile processed 
    time_end = timestamp

    return (
        const_dict["product_id"],
        time_begin,
        time_end,
        ubt_data.param_us_dicts,
        ubt_data.data_us_dicts,
        ubt_data.data_dicts,
        settings_dict,
    )