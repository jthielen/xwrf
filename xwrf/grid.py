"""Provide grid-related functionality specific to WRF datasets.

This submodule contains code reused with modification from Salem under the terms of the BSD
3-Clause License. Salem is Copyright (c) 2014-2021, Fabien Maussion and Salem Development Team All
rights reserved.
"""

import numpy as np
import pyproj


# Default CRS (lon/lat on WGS84, which is EPSG:4326)
wgs84 = pyproj.CRS(4326)

# WRF dimension names
_HORIZONTAL_DIMS = ['south_north', 'west_east', 'south_north_stag', 'west_east_stag']


def _wrf_grid_from_dataset(ds):
    """Get the WRF projection and dimension coordinates out of the file."""

    pargs = {
        'x_0': 0,
        'y_0': 0,
        'a': 6370000,
        'b': 6370000
    }
    if hasattr(ds, 'PROJ_ENVI_STRING'):
        # HAR and other TU Berlin files
        dx = ds.GRID_DX
        dy = ds.GRID_DY
        pargs['lat_1'] = ds.PROJ_STANDARD_PAR1
        pargs['lat_2'] = ds.PROJ_STANDARD_PAR2
        pargs['lat_0'] = ds.PROJ_CENTRAL_LAT
        pargs['lon_0'] = ds.PROJ_CENTRAL_LON
        pargs['center_lon'] = ds.PROJ_CENTRAL_LON
        if ds.PROJ_NAME in ['Lambert Conformal Conic',
                            'WRF Lambert Conformal']:
            proj_id = 1
        else:
            proj_id = 99  # pragma: no cover
    else:
        # Normal WRF file
        cen_lon = ds.CEN_LON
        cen_lat = ds.CEN_LAT
        dx = ds.DX
        dy = ds.DY
        pargs['lat_1'] = ds.TRUELAT1
        pargs['lat_2'] = ds.TRUELAT2
        pargs['lat_0'] = ds.MOAD_CEN_LAT
        pargs['lon_0'] = ds.STAND_LON
        pargs['center_lon'] = ds.CEN_LON
        proj_id = ds.MAP_PROJ

    if proj_id == 1:
        # Lambert
        pargs['proj'] = 'lcc'
        del pargs['center_lon']
    elif proj_id == 2:
        # Polar stereo
        pargs['proj'] = 'stere'
        pargs['lat_ts'] = pargs['lat_1']
        pargs['lat_0'] = 90.
        del pargs['lat_1'], pargs['lat_2'], pargs['center_lon']
    elif proj_id == 3:
        # Mercator
        pargs['proj'] = 'merc'
        pargs['lat_ts'] = pargs['lat_1']
        pargs['lon_0'] = pargs['center_lon']
        del pargs['lat_0'], pargs['lat_1'], pargs['lat_2'], pargs['center_lon']
    else:
        raise NotImplementedError(f'WRF proj not implemented yet: {proj_id}')

    # Construct the pyproj CRS (letting errors fail through)
    crs = pyproj.CRS(pargs)

    # Get grid specifications
    nx = ds.dims['west_east']
    ny = ds.dims['south_north']
    if hasattr(ds, 'PROJ_ENVI_STRING'):
        # HAR
        x0 = ds['west_east'][0]
        y0 = ds['south_north'][0]
    else:
        # Normal WRF file
        trf = pyproj.Transformer.from_crs(wgs84, crs)
        e, n = trf.transform(cen_lon, cen_lat)
        x0 = -(nx - 1) / 2. * dx + e  # DL corner
        y0 = -(ny - 1) / 2. * dy + n  # DL corner

    return {
        'crs': crs,
        'south_north': y0 + np.arange(ny) * dy,
        'west_east': x0 + np.arange(nx) * dx,
        'south_north_stag': y0 + (np.arange(ny + 1) - 0.5) * dy,
        'west_east_stag': x0 + (np.arange(nx + 1) - 0.5) * dx,
    }


def add_horizontal_projection_coordinates(dataset):
    """Add missing horizontal projection coordinates and grid mapping to dataset."""
    crs, south_north, west_east, south_north_stag, west_east_stag = (
        _wrf_grid_from_dataset(dataset)
    )

    # Add grid center coordinates
    dataset['south_north'] = (
        'south_north',
        south_north,
        {'units': 'm', 'standard_name': 'projection_y_coordinate', 'axis': 'Y'}
    )
    dataset['west_east'] = (
        'west_east',
        south_north,
        {'units': 'm', 'standard_name': 'projection_x_coordinate', 'axis': 'X'}
    )

    # Optionally add staggered grid (cell boundary) coordinates
    if 'south_north_stag' in dataset.dims:
        dataset['south_north_stag'] = (
            'south_north_stag',
            south_north_stag,
            {
                'units': 'm',
                'standard_name': 'projection_y_coordinate',
                'axis': 'Y',
                'c_grid_axis_shift': 0.5
            }
        )
    if 'west_east_stag' in dataset.dims:
        dataset['west_east_stag'] = (
            'west_east_stag',
            west_east_stag,
            {
                'units': 'm',
                'standard_name': 'projection_x_coordinate',
                'axis': 'X',
                'c_grid_axis_shift': 0.5
            }
        )

    # Add CF grid mapping
    dataset['wrf_projection'] = (tuple(), crs, crs.to_cf())
    for varname in dataset.data_vars:
        if any(dim in dataset[varname].dims for dim in _HORIZONTAL_DIMS):
            dataset[varname].attrs['grid_mapping'] = 'wrf_projection'

    return dataset
