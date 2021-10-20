# -*- coding: UTF_8 -*-

# @copyright  this code is the property of Ubertone.
# You may use this code for your personal, informational, non-commercial purpose.
# You may not distribute, transmit, display, reproduce, publish, license, create derivative works from, transfer or sell any information, software, products or services based on this code.
# @origin: @author Stéphane Fischer, @version 1.4 @date 24 mai 2015 - 04 octobre 2016
# author: Stéphane Fischer, MB, MP

# lecture du fichier de données
# se lance :
# python3 ./raw_extract.py --settings="" --input=/Users/san/Desktop/raw_eawag/raw_20150430T093840_001.udt --output=./test_dest/
# python3 ./raw_extract.py --settings="" --input='/home/san/data/Work/Projets/2016_bistatic/Test_travers_paroi_160427/raw_20160427T191755_001.udt'  --output='/home/san/data/Work/Projets/2016_bistatic/Test_travers_paroi_160427'

from optparse import OptionParser
import json
from datetime import datetime  # pour time count

from ubt_raw_file import ubt_raw_file
from ubt_raw_data import ubt_raw_data
from ubt_raw_flag import *
from ubt_raw_config import (
    read_blind_ca_v2,
    paramus_rawdict2ormdict,
)  # , ubt_raw_config


def parse_arg(_argv):
    """Parse data"""
    param = {}
    # Deprecated since version 2.7: use the argparse module.
    parser = OptionParser()
    # Define option
    parser.add_option("--input", help="raw data file", type="string")
    parser.add_option(
        "--output",
        help="destination path for the extracted data",
        type="string",
        default="./",
    )
    # Parse arguments and options
    param["options"], param["args"] = parser.parse_args(_argv[1:])

    return param["options"], param["args"]


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

    # les config HW (toujours écrits dans l'ordre dans le raw)
    # we use a list with config id (0..N-1) as index
    # configs_hw = []
    blind_ca0 = []
    blind_ca1 = []

    i_prof = 0
    try:
        while 1:
            flag, size, data = fileraw.read_chunk()

            # print("flag = %d with size %d" % (flag, size))

            # Pour raw UDT005, ie. UB-Lab P, on peut rencontrer 4 flags: const, settings json, configs (HW), profils
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
                print("device: %s" % const_dict["product_id"])

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
                param_us_dicts = paramus_rawdict2ormdict(settings_dict)

            # configs HW est utilisé pour la conversion des données de profils codés en human readable.
            if flag == CONFIG_TAG:
                # configs_hw.append(ubt_raw_config(flag, size, data, const_dict["hardware"]["f_sys"]))
                # what is needed from here and which is not in param_us_dict is only blind_ca0 and blind_ca1
                blind_ca = read_blind_ca_v2(size, data)
                blind_ca0.append(blind_ca[0])
                blind_ca1.append(blind_ca[1])

            if flag == PROFILE_TAG:
                if i_prof == 0:
                    # ubt_data = ubt_raw_data(configs_hw)
                    ubt_data = ubt_raw_data(
                        param_us_dicts, blind_ca0, blind_ca1
                    )

                i_prof += 1

                ubt_data.read_line(size, data)
                # first timestamp of udt file for time_begin definition of run:
                if i_prof == 1:
                    time_begin = min(
                        ubt_data.data_us_dicts[ubt_data.current_config][
                            ubt_data.current_channel
                        ][
                            list(
                                ubt_data.data_us_dicts[ubt_data.current_config][
                                    ubt_data.current_channel
                                ].keys()
                            )[0]
                        ][
                            "time"
                        ][
                            0
                        ],
                        ubt_data.data_dicts[
                            list(ubt_data.data_dicts.keys())[0]
                        ]["time"][0],
                    )

    except KeyboardInterrupt:
        print("read interrupted by user")
    except EOFError:
        print("End of file")
    except:
        print("Error")
        raise

    print("%d profiles read" % i_prof)
    # last timestamp of udt file for time_end definition of run:
    time_end = max(
        ubt_data.data_us_dicts[ubt_data.current_config][
            ubt_data.current_channel
        ][
            list(
                ubt_data.data_us_dicts[ubt_data.current_config][
                    ubt_data.current_channel
                ].keys()
            )[0]
        ][
            "time"
        ][
            -1
        ],
        ubt_data.data_dicts[list(ubt_data.data_dicts.keys())[0]]["time"][-1],
    )

    return (
        const_dict["product_id"],
        time_begin,
        time_end,
        param_us_dicts,
        ubt_data.data_us_dicts,
        ubt_data.data_dicts,
        settings_dict,
    )


# # Parsing args
# param, files_arg = parse_arg(sys.argv)
#
# raw_extract(param.input, "%s/" % param.output)
# FOR DEV_TEST:
if __name__ == "__main__":
    path = "./raw_test.udt"
    extract_start = datetime.now()
    (
        device_name,
        time_begin,
        time_end,
        param_us_dicts,
        data_us_dicts,
        data_dicts,
        settings_dict
    ) = raw_extract(path)
    print(
        "=============\nextract duration:%s\n==========="
        % (datetime.now() - extract_start)
    )
    print(device_name)
    print(time_begin, time_end)
    print(param_us_dicts)
    #print(data_dicts)
    #print(data_us_dicts)
