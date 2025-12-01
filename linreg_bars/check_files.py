import os
import glob

data_dir = r"C:\Users\kvanh\Documents\dev\GitHub\stock_data\Trade Experiments\historical_data\11_22_25_daily"
print(f"Checking directory: {data_dir}")

if not os.path.exists(data_dir):
    print("Directory does not exist!")
else:
    files = glob.glob(os.path.join(data_dir, "*.csv"))
    print(f"Found {len(files)} CSV files.")
    if len(files) > 0:
        print("First 5 files:")
        for f in files[:5]:
            print(os.path.basename(f))
