"""
GLODAP
======
Download GLODAP (https://glodap.info) datasets and import them as pandas
DataFrames.

The functions `arctic`, `atlantic`, `indian`, `pacific` and `world` import the
latest version of the GLODAP dataset for the corresponding region, first
downloading the file if it's not already saved locally.  For example:

  >>> import glodap
  >>> df_atlantic = glodap.atlantic()

Files are saved by default at "~/.glodap", but this can be controlled with the
kwarg `gpath`.  See the function docstrings for more information.

The columns of the imported DataFrames are renamed so that they can be passed
directly into PyCO2SYS v2:

  >>> import PyCO2SYS as pyco2
  >>> co2s_atlantic = pyco2.sys(data=df_atlantic, nitrite=None)

Note `nitrite=None` - this means PyCO2SYS will ignore the "nitrite" column,
which is necessary because PyCO2SYS includes the nitrite-nitrous acid
equilibrium but its equilibrium constant is valid only under lab conditions.

The columns are the same as in the original GLODAP .mat files, except:
  * The "G2" at the start of each parameter has been removed.
  * Flags end with "_f" instead of just "f".
  * There is a "datetime" column, which combines the "year", "month" and "day"
    but NOT the "hour" and "minute" (because some of these are missing).
  * For compatibility with PyCO2SYS:
              "tco2" => "dic"
              "talk" => "alkalinity"
          "phts25p0" => "ph_lab"
      "phtsinsitutp" => "ph_insitu"
    Therefore when passing the DataFrame directly to PyCO2SYS as in the example
    above, the system will be solved from DIC and alkalinity, not pH.

The functions `download` and `read` can also be used for finer control, such as
specifying a particular GLODAP version rather than using the latest one.  See
their function docstrings for more information.
"""

import os
from warnings import warn

import pandas as pd
import requests
from scipy.io import loadmat


# Package metadata
__author__ = "Humphreys, Matthew P."
__version__ = "0.1"

# GLODAP metadata
version_latest = "v2.2023"
versions = ["v2.2023", "v2.2022", "v2.2021", "v2.2020", "v2.2019"]
regions_full = {
    "arctic": "Arctic_Ocean",
    "atlantic": "Atlantic_Ocean",
    "indian": "Indian_Ocean",
    "pacific": "Pacific_Ocean",
    "global": "Merged_Master_File",
    "world": "Merged_Master_File",
}
regions = regions_full.copy()
for k, v in regions_full.items():
    regions[k[:3]] = v


def _get_paths(region, version, gpath):
    assert region in regions, "`region` not valid!"
    if version is None:
        version = version_latest
    assert version in versions, "`version` not valid!"
    if gpath is None:
        gpath = os.path.join(os.path.expanduser("~"), ".glodap")
    fileregion = regions[region.lower()]
    filename = f"{fileregion}_{version}.mat"
    return gpath, fileregion, filename, version


def download(region="world", version=None, gpath=None, do_download=True):
    """Download a GLODAP data file and save it locally.

    Parameters
    ----------
    region : str, optional
        Which GLODAP region to download, by default "world", which is the
        Merged Master File.  The options are:
            "arctic"    "arc"   Arctic Ocean
            "atlantic"  "atl"   Atlantic Ocean
            "indian"    "ind"   Indian Ocean
            "pacific"   "pac"   Pacific Ocean
            "world"     "wor"   Merged Master File
            "global"    "glo"   Merged Master File
    version : str or None, optional
        Which GLODAP version to download, by default `None`, in which case the
        most recent version is downloaded.  The options are:
            "v2.2023", "v2.2022", "v2.2021", "v2.2020", "v2.2019"
    gpath : str of None, optional
        Where to save the downloaded file, by default `None`, in which case the
        file is saved at "~/.glodap".
    do_download : bool, optional
        Whether to actually download the file, by default `True`.

    Returns
    -------
    int
        The status code from the URL request; 200 indicates success.
    """
    gpath, fileregion, filename, version = _get_paths(region, version, gpath)
    if not os.path.isdir(gpath):
        os.makedirs(gpath)
    url = (
        f"https://glodap.info/glodap_files/{version}/"
        + f"GLODAP{version}_{fileregion}.mat"
    )
    if do_download:
        r = requests.get(url)
        if r.status_code == 200:
            with open(os.path.join(gpath, filename), "wb") as file:
                file.write(r.content)
        else:
            warn(f"Could not download file - status code {r.status_code}")
    else:
        r = requests.head(url)
    return r.status_code


def read(region="world", version=None, gpath=None, rename_pyco2=True):
    """Import a GLODAP data file as a pandas DataFrame, downloading it first
    if it's not already available locally.

    Parameters
    ----------
    region : str, optional
        Which GLODAP region to import, by default "world", which is the
        Merged Master File.  The options are:
            "arctic"    "arc"   Arctic Ocean
            "atlantic"  "atl"   Atlantic Ocean
            "indian"    "ind"   Indian Ocean
            "pacific"   "pac"   Pacific Ocean
            "world"     "wor"   Merged Master File
            "global"    "glo"   Merged Master File
    version : str or None, optional
        Which GLODAP version to import, by default `None`, in which case the
        most recent version is imported.  The options are:
            "v2.2023", "v2.2022", "v2.2021", "v2.2020", "v2.2019"
    gpath : str of None, optional
        Where to the downloaded file is or should be saved, by default `None`,
        in which case the file is imported from or saved at "~/.glodap".
    rename_pyco2 : bool, optional
        Whether to rename the columns to work with PyCO2SYS, by default `True`.

    Returns
    -------
    pd.DataFrame
        The GLODAP dataset as a pandas DataFrame.
    """
    gpath, _, filename, version = _get_paths(region, version, gpath)
    try:
        df = loadmat(os.path.join(gpath, filename))
    except FileNotFoundError:
        download(region=region, version=version, gpath=gpath)
        df = loadmat(os.path.join(gpath, filename))
    df = pd.DataFrame(
        {
            k[2:]: [w[0][0] for w in v] if v.dtype == "O" else v.ravel()
            for k, v in df.items()
            if k.startswith("G2")
        }
    )
    # Convert columns that should be integers into integers
    # Can't convert cast, hour, minute to integers because they have missing
    # values
    keys_integers = [
        "cruise",
        "station",
        "region",
        # "cast",
        "year",
        "month",
        "day",
        # "hour",
        # "minute",
    ]
    keys_flags = [
        "salinityf",
        "oxygenf",
        "aouf",
        "nitratef",
        "nitritef",
        "silicatef",
        "phosphatef",
        "tco2f",
        "talkf",
        "fco2f",
        "phts25p0f",
        "phtsinsitutpf",
        "cfc11f",
        "cfc12f",
        "cfc113f",
        "ccl4f",
        "sf6f",
        "c13f",
        "c14f",
        "h3f",
        "he3f",
        "hef",
        "neonf",
        "o18f",
        "tocf",
        "docf",
        "donf",
        "tdnf",
        "chlaf",
    ]
    for k in keys_integers + keys_flags:
        df[k] = df[k].astype(int)
    # Rename columns for PyCO2SYS, if requested
    if rename_pyco2:
        renamer_pyco2 = {
            "tco2": "dic",
            "talk": "alkalinity",
            "phts25p0": "ph_lab",
            "phtsinsitutp": "ph_insitu",
        }
        renamer_flags = {
            k: renamer_pyco2[k[:-1]] + "_f"
            if k[:-1] in renamer_pyco2
            else k[:-1] + "_f"
            for k in keys_flags
        }
        df = df.rename(columns=renamer_pyco2).rename(columns=renamer_flags)
    # Calculate datetime for convenience - don't include hour and minute
    # because some are missing
    df["datetime"] = pd.to_datetime(
        df[
            [
                "year",
                "month",
                "day",
                # "hour",
                # "minute",
            ]
        ]
    )
    return df


def arctic(gpath=None, rename_pyco2=True):
    """Import the latest version of the GLODAP Arctic Ocean dataset,
    downloading it first if it's not already available locally.

    Parameters
    ----------
    gpath : str of None, optional
        Where to the downloaded file is or should be saved, by default `None`,
        in which case the file is imported from or saved at "~/.glodap".
    rename_pyco2 : bool, optional
        Whether to rename the columns to work with PyCO2SYS, by default `True`.

    Returns
    -------
    pd.DataFrame
        The GLODAP Arctic Ocean dataset as a pandas DataFrame.
    """
    return read(region="arctic", gpath=gpath, rename_pyco2=rename_pyco2)


def atlantic(gpath=None, rename_pyco2=True):
    """Import the latest version of the GLODAP Atlantic Ocean dataset,
    downloading it first if it's not already available locally.

    Parameters
    ----------
    gpath : str of None, optional
        Where to the downloaded file is or should be saved, by default `None`,
        in which case the file is imported from or saved at "~/.glodap".
    rename_pyco2 : bool, optional
        Whether to rename the columns to work with PyCO2SYS, by default `True`.

    Returns
    -------
    pd.DataFrame
        The GLODAP Atlantic Ocean dataset as a pandas DataFrame.
    """
    return read(region="atlantic", gpath=gpath, rename_pyco2=rename_pyco2)


def indian(gpath=None, rename_pyco2=True):
    """Import the latest version of the GLODAP Indian Ocean dataset,
    downloading it first if it's not already available locally.

    Parameters
    ----------
    gpath : str of None, optional
        Where to the downloaded file is or should be saved, by default `None`,
        in which case the file is imported from or saved at "~/.glodap".
    rename_pyco2 : bool, optional
        Whether to rename the columns to work with PyCO2SYS, by default `True`.

    Returns
    -------
    pd.DataFrame
        The GLODAP Indian Ocean dataset as a pandas DataFrame.
    """
    return read(region="indian", gpath=gpath, rename_pyco2=rename_pyco2)


def pacific(gpath=None, rename_pyco2=True):
    """Import the latest version of the GLODAP Pacific Ocean dataset,
    downloading it first if it's not already available locally.

    Parameters
    ----------
    gpath : str of None, optional
        Where to the downloaded file is or should be saved, by default `None`,
        in which case the file is imported from or saved at "~/.glodap".
    rename_pyco2 : bool, optional
        Whether to rename the columns to work with PyCO2SYS, by default `True`.

    Returns
    -------
    pd.DataFrame
        The GLODAP Pacific Ocean dataset as a pandas DataFrame.
    """
    return read(region="pacific", gpath=gpath, rename_pyco2=rename_pyco2)


def world(gpath=None, rename_pyco2=True):
    """Import the latest version of the GLODAP Merged Master File dataset,
    downloading it first if it's not already available locally.

    Parameters
    ----------
    gpath : str of None, optional
        Where to the downloaded file is or should be saved, by default `None`,
        in which case the file is imported from or saved at "~/.glodap".
    rename_pyco2 : bool, optional
        Whether to rename the columns to work with PyCO2SYS, by default `True`.

    Returns
    -------
    pd.DataFrame
        The GLODAP Merged Master File as a pandas DataFrame dataset.
    """
    return read(region="world", gpath=gpath, rename_pyco2=rename_pyco2)
