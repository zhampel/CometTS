from __future__ import print_function

try:
    import os
    import sys 
    import argparse
    import numpy as np 
    import matplotlib.pyplot as plt
    
    from cometts import CSV_It

except ImportError as e:
    print(e)
    raise ImportError

    
    
def main():
    global args
    parser = argparse.ArgumentParser(description="CSV file generator required for CometTS analysis")
    parser.add_argument("-i", "--input_dir", dest="input_dir", required=True, help="Input data directory")
    parser.add_argument("-o", "--output_dir", dest="output_dir", required=True, help="Output directory for CSV file")
    parser.add_argument("-t", "--ts_prefix", dest="ts_prefix", default="S*rade9.tif", help="Time series naming pattern")
    parser.add_argument("-s", "--obs_prefix", dest="obs_prefix", default="S*cvg.tif", help="Observation naming pattern")
    parser.add_argument("-m", "--mask_prefix", dest="mask_prefix", default="S*cvg.tif", help="Mask naming pattern")
    parser.add_argument("-d", "--date_loc", dest="date_loc", default="10:18", help="Location of date characters in file name")
    parser.add_argument("-b", "--band_num", dest="band_num", default="", help="Location of band number in file name")

    args = parser.parse_args()

    # Get input arguments
    input_dir = args.input_dir
    output_dir = args.output_dir
    ts_prefix = args.ts_prefix
    obs_prefix = args.obs_prefix
    mask_prefix = args.mask_prefix
    date_loc = args.date_loc
    band_num = args.band_num

    # Generate CSV file
    gdf_out = CSV_It(input_dir, ts_prefix, obs_prefix, mask_prefix, date_loc, band_num)
    output = os.path.join(output_dir, 'Raster_List.csv')
    gdf_out.to_csv(output)


if __name__ == "__main__":
    main()
