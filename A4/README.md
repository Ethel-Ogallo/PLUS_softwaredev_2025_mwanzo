### Sentinel-1 processing using esa-snappy  
To use this notebook with the esa-snappy library (the Python interface for ESA SNAP), follow these steps:

**1. Create and activate a conda environment**   
`` conda create -n snap_env python=3.9 ``   
`` conda activate snap_env ``    
`` python -m pip install esa-snappy ``  

**2. Install ESA SNAP Desktop**    
Download and install ESA SNAP from the [SNAP website](https://earth.esa.int/eogateway/tools/snap).  
During installation, enable the option to configure Python for SNAP and specify your Python executable path:  
Use the Python from your conda environment, e.g. *C:\Users\YourUsername\.conda\envs\snap_env\python.exe*  
If that does not work, try the base environment Python: for example *(C:\ProgramData\Anaconda3\python.exe)*   

**3. Run the snappy-conf script to configure SNAP**  
If you use the base environemnt python or you already have SNAP installed then,  
Open a command prompt, navigate to SNAP’s bin folder, and run:  
`` cd "C:\Program Files\esa-snap\bin" ``  
`` snappy-conf "C:\Users\YourUsername\.conda\envs\snap_env\python.exe" ``  
You should see: *Configuration finished successfully!*

**4. Verify esa-snappy works**  
Activate your environment and open Python:  
`` conda activate snap_env  ``  
`` python  ``
  
in the Python environment, try importing:  
``  import esa_snappy ``  
`` from esa_snappy import ProductIO ``    
If no errors occur, your setup is complete!  

### Data
To access the data (too large to add here) used in this notebook. Download it from [here](https://browser.stac.dataspace.copernicus.eu/collections/sentinel-1-grd/items/S1C_IW_GRDH_1SDV_20250527T181900_20250527T181925_002520_0053F6_70DB_COG?.language=en&.asset=asset-product)
