"""Provide lazy calculation of physical variables from esoteric WRF components.

Only four fields are implemented here:
- air_potential_temperature (from T)
- air_pressure (from P and PB)
- geopotential (from PH and PHB)
- geopotential_height (from geopotential)

All other typical diagnostics (like air_temperature, etc.) are calculable using these fields (and
those otherwise present) using a general-purpose toolkit.
"""


def _check_if_dask(dataarray):
    # TODO: this needs to actually do something, however, TBD how to work through the chunks arg
    # in the backend API (otherwise, weird conflicts may occur)
    return True


def calc_base_diagnostics(dataset, drop=True):
    """Calculate the four basic fields that WRF does not have in physically meaningful form.

    Parameters
    ----------
    dataset : xarray.Dataset
        Dataset representing WRF data opened via NetCDF4 backend with chunking.
    drop : bool
        Decide whether to drop the components of origin after creating the diagnostic fields from
        them.

    Notes
    -----
    This operation should be called before destaggering or any other cleaning operation.
    """
    # Potential temperature
    if _check_if_dask(dataset['T']):
        dataset['air_potential_temperature'] = dataset['T'] + 300
        dataset['air_potential_temperature'].attrs = {
            'units': 'K',
            'standard_name': 'air_potential_temperature'
        }
        if drop:
            del dataset['T']

    # Pressure
    if _check_if_dask(dataset['P']) and _check_if_dask(dataset['PB']):
        dataset['air_pressure'] = dataset['P'] + dataset['PB']
        dataset['air_pressure'].attrs = {
            'units': dataset['P'].attrs.get('units', 'Pa'),
            'standard_name': 'air_pressure'
        }
        if drop:
            del dataset['P'], dataset['PB']

    # Geopotential and geopotential height
    if _check_if_dask(dataset['PH']) and _check_if_dask(dataset['PHB']):
        dataset['geopotential'] = dataset['PH'] + dataset['PHB']
        dataset['geopotential'].attrs = {
            'units': 'm**2 s**-2',
            'standard_name': 'geopotential'
        }
        dataset['geopotential_height'] = dataset['geopotential'] / 9.81
        dataset['geopotential_height'].attrs = {
            'units': 'm',
            'standard_name': 'geopotential_height'
        }
        if drop:
            del dataset['PH'], dataset['PHB']

    return dataset
