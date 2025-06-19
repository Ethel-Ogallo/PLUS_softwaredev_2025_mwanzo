"""
Preprocessing Sentinel-1 GRD product

This script allows for processing Sentinel-1 SAR GRD products using esa_snappy library,
following the SNAP workflow funxtions which are to be used in sequence:
    load .SAFE file 
    subset AOI
    applying orbit files 
    thermal noise removal 
    radiometric calibration 
    speckle filtering 
    terrain correction.

Included is a helper function 'plotBand' for visualizing the SAR product.
"""

import os
import esa_snappy
import numpy as np
import matplotlib.pyplot as plt

from esa_snappy import Product, ProductIO, ProductUtils, WKTReader, HashMap, GPF, jpy



# Loads the SNAP operators globally when the module is imported
GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()

def read_SAFE_product(file_path):
    """
    Reads a Sentinel-1 SAR GRD product from a .SAFE directory or a .zip archive.

    This function utilizes ESA SNAP's `ProductIO.readProduct` to load the SAR data
    into a SNAP Product object, which is the base object for further processing.

    Args:
        file_path (str): The file path to the Sentinel-1 .SAFE directory (unzipped)
                        or the .zip archive containing the GRD product.

    Returns:
        esa_snappy.Product: A SNAP Product object representing the loaded SAR data.

    Raises:
        FileNotFoundError: If the specified zip_path does not exist.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Product path not found: {file_path}")
    
    print(f"Reading SAR product from: {file_path}...")
    product = ProductIO.readProduct(file_path)
    print("\tProduct read successfully.")
    return product

def apply_orbit_file(product):
    """
    Applies precise satellite orbit file to the SAR product.

    This operation orthorectifies the SAR product to improve accuracy by using 
    precise orbit information.

    Args:
        product (esa_snappy.Product): The input SAR Product object.

    Returns:
        esa_snappy.Product: The product with orbit file applied.
    """
    print('\tApplying Orbit File...')
    parameters = HashMap() 
    parameters.put('orbitType', 'Sentinel Precise (Auto Download)') # 'Sentinel Precise (Auto Download) specifically for Sentinel-1
    parameters.put('continueOnFail', 'false') # Do not continue if orbit file application fails
    
    output = GPF.createProduct('Apply-Orbit-File', parameters, product)
    print('\tOrbit File applied.')
    return output

def subset_AOI(product, bbox) :
    """
    The raw image is too large to process, theredore to reduce resources 
    required to process, the product is subset to a specific AOI.

    Args:
        product (esa_snappy.Product): Input SAR product.
        bbox (list): Bounding box as [minLon, minLat, maxLon, maxLat].

    Returns:
        esa_snappy.Product: Subsetted product.

    Raises:
        ValueError: If bbox is None or invalid.
    """
    if not bbox or len(bbox) != 4:
        raise ValueError("bbox must be a list of [minLon, minLat, maxLon, maxLat]")

    print('\tSubsetting using bounding box:', bbox)

    WKTReader_snappy = jpy.get_type('org.locationtech.jts.io.WKTReader')

    # Create WKT polygon string from bbox
    geometry_wkt = (
        f"POLYGON(({bbox[0]} {bbox[1]}, {bbox[2]} {bbox[1]}, "
        f"{bbox[2]} {bbox[3]}, {bbox[0]} {bbox[3]}, {bbox[0]} {bbox[1]}))"
    )

    parameters = HashMap()
    parameters.put('copyMetadata', True)

    try:
        geometry = WKTReader_snappy().read(geometry_wkt)
        parameters.put('geoRegion', geometry)
    except Exception as e:
        raise RuntimeError(f"Error converting WKT to SNAP geometry: {e}\nWKT: {geometry_wkt}")

    output = GPF.createProduct('Subset', parameters, product)
    print('\tProduct subsetted.')
    return output


def thermal_noise_removal(product) :
    """
    Removes thermal noise from the SAR product.

    Thermal noise is a constant noise floor that affects SAR images, especially
    in low-backscatter areas. This step removes this noise, improving the signal-to-noise ratio.

    Args:
        product (esa_snappy.Product): The input SAR Product object.

    Returns:
        esa_snappy.Product: The product after thermal noise removal.
    """
    print('\tPerforming thermal noise removal...')
    parameters = HashMap()
    parameters.put('removeThermalNoise', True)
    output = GPF.createProduct('ThermalNoiseRemoval', parameters, product)
    print('\tThermal noise removed.')
    return output

def radiometric_calibration(product, polarization, pols_selected) :
    """
    Performs radiometric calibration on the SAR product.

    Calibration converts the raw SAR data into radar brightness values.

    Args:
        product (esa_snappy.Product): The input SAR Product object.
        polarization (str): the desired output polarization type.
        pols_selected (str): the polarizations to be calibrated

    Returns:
        esa_snappy.Product: The radiometrically calibrated SAR Product object.

    Raises:
        ValueError: If an unsupported 'polarization' type is provided.
    """
    print(f'\tRadiometric calibration for polarization(s): {pols_selected}...')
    parameters = HashMap()
    parameters.put('outputSigmaBand', True)
    parameters.put('outputImageScaleInDb', False) # Output linear scale, not dB

    # Determine source bands based on the input polarization type
    if polarization == 'DH':  # Dual-horizontal: HH, HV
        parameters.put('sourceBands', 'Intensity_HH,Intensity_HV')
    elif polarization == 'DV': # Dual-vertical: VH, VV
        parameters.put('sourceBands', 'Intensity_VH,Intensity_VV')
    elif polarization == 'SH' or polarization == 'HH': # Single-horizontal: HH
        parameters.put('sourceBands', 'Intensity_HH')
    elif polarization == 'SV' or polarization == 'VV': # Single-vertical: VV
        parameters.put('sourceBands', 'Intensity_VV')
    else:
        raise ValueError(f"Unsupported polarization type: {polarization}. "
                         "Please use 'DH', 'DV', 'SH'/'HH', or 'SV'/'VV'.")
    
    # This parameter directly controls which output bands are generated
    parameters.put('selectedPolarisations', pols_selected) 

    output = GPF.createProduct("Calibration", parameters, product)
    print('\tRadiometric calibration completed.')
    return output

def speckle_filtering(product, filter_type = 'Lee', filter_size = 5):
    """
    Applies speckle filtering to the SAR product.

    Speckle Filtering reduces granular noise while attempting to preserve target features.

    Args:
        product (esa_snappy.Product): The input SAR Product object.
        filter_type (str, optional): The type of speckle filter to apply.Defaults to 'Lee'.
        filter_size (int, optional): The size of the filter window.Defaults to 5x5 filter.

    Returns:
        esa_snappy.Product: The speckle-filtered SAR Product object.
    """
    print(f'\tApplying {filter_type} speckle filter with size {filter_size}x{filter_size}...')
    Integer = jpy.get_type('java.lang.Integer') # Java Integer type for parameters

    parameters = HashMap()
    parameters.put('filter', filter_type)
    parameters.put('filterSizeX', Integer(filter_size))
    parameters.put('filterSizeY', Integer(filter_size))
    
    output = GPF.createProduct('Speckle-Filter', parameters, product)
    print('\tSpeckle filtering completed.')
    return output

def terrain_correction(product, dem_name, pixel_spacing) :
    """
    Applies Range-Doppler Terrain Correction to the SAR product.

    This corrects for geometric distortions caused by topography and
    sensor tilt, projecting the image into a specified map projection.

    Args:
        product (esa_snappy.Product): The input SAR Product object.
        dem_name (str): the Digital Elevation Model (DEM) to use
                        (e.g., 'GETASSE30', 'SRTM 1Sec HGT').
        pixel_spacing (float): The desired pixel spacing in meters of the output image.
                                Defaults to 10.0 (for Sentinel-1 GRD).

    Returns:
        esa_snappy.Product: The terrain-corrected SAR Product object.
    """
    print(f'\tApplying terrain correction with DEM: {dem_name}, pixel spacing: {pixel_spacing}..')
    params = HashMap()
    params.put('demName', dem_name)
    params.put('pixelSpacingInMeter', pixel_spacing)
    
    output = GPF.createProduct('Terrain-Correction', params, product)
    print('\tTerrain correction completed.')
    return output

## Helper function
def plotBand(product, band_name, vmin=None, vmax=None, cmap=plt.cm.binary, figsize=(10, 10)):
    """
    Plots a specific band from a SNAP Product object using matplotlib.

    This is a utility function for quick visualization of product bands.

    Args:
        product (esa_snappy.Product): The input SNAP Product object.
        band_name (str): The name of the band to plot (e.g., 'Intensity_VV', 'Sigma0_VV').
        vmin (float): Minimum value for colormap scaling. If None, automatically determined.
        vmax (float): Maximum value for colormap scaling. If None, automatically determined.
        cmap (matplotlib.colors.Colormap, optional): Colormap to use. Defaults to grayscale.
        figsize (tuple, optional): Figure size for the plot. Defaults to (10, 10).
    
    Returns:
        matplotlib.image.AxesImage: The image plot object.
    
    Raises:
        ValueError: If the specified band_name does not exist in the product.
    """
    band = product.getBand(band_name)
    if band is None:
        raise ValueError(f"Band '{band_name}' not found in product.")

    w = band.getRasterWidth()
    h = band.getRasterHeight()
    print(f"Band dimensions: {w} x {h}")

    band_data = np.zeros(w * h, np.float32)
    band.readPixels(0, 0, w, h, band_data)
    band_data.shape = (h, w)

    plt.figure(figsize=figsize)
    imgplot = plt.imshow(band_data, cmap=cmap, vmin=vmin, vmax=vmax)
    plt.title(f"Band: {band_name}")
    plt.show()
    return imgplot