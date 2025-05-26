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

The columns of the imported DataFrames can be passed directly into PyCO2SYS v2:

  >>> import PyCO2SYS as pyco2
  >>> co2s_atlantic = pyco2.sys(data=df_atlantic, nitrite=None)

Note `nitrite=None` - this means PyCO2SYS will ignore the "nitrite" column,
which is necessary because while PyCO2SYS includes the nitrite-nitrous acid
equilibrium, its equilibrium constant is valid only under lab conditions.

Because of how the columns are named, when passing the DataFrame directly to
PyCO2SYS as above, the system will be solved from DIC and alkalinity, not pH.

The columns are the same as in the original GLODAP .mat files, except:
  * The "G2" at the start of each parameter has been removed.
  * Flags end with "_f" instead of just "f".
  * There is a "datetime" column, which combines the "year", "month" and "day"
    but NOT the "hour" and "minute" (because some of these are missing).

The functions `download` and `read` can also be used for finer control, such as
specifying a particular GLODAP version rather than using the latest one.  See
their function docstrings for more information.

The .mat files from the GEOMAR mirrors are downloaded, and the SHA256 checksum
of each downloaded file is checked before the file is written to disk.
"""

import hashlib
import os
import tempfile
from warnings import warn

import pandas as pd
import requests
from scipy.io import loadmat


# Package metadata
__author__ = "Humphreys, Matthew P."
__version__ = "0.3"

# GLODAP metadata
version_latest = "v2.2023"
versions = ["v2.2023", "v2.2022", "v2.2021", "v2.2020", "v2.2019"]
regions = {
    "arctic": "Arctic_Ocean",
    "atlantic": "Atlantic_Ocean",
    "indian": "Indian_Ocean",
    "pacific": "Pacific_Ocean",
    "world": "Merged_Master_File",
}
regions_full = regions.copy()
for k, v in regions.items():
    regions_full[k[:3]] = v
checksums = {
    "v2.2023": {
        "arc": "a998a8d99db84e9357b21a7e345bbfde62eae77870e651119b4c1929a2f1e2fd",
        "atl": "a3ff7bc4f4ff3a1b0f540886a0eb7c9b3ec52aa4eae2dea57d47ae61f56da56f",
        "ind": "8c9c21d4af9db506b09fdec79e2a311c2dbbf41b8fc4e6a7a855d1d50b3ccb51",
        "pac": "9891160dba6211d2f13923171564a06bbea34cda799f3091148061c32fc6070c",
        "wor": "002881fa71923d15c1bd5aca3b99bc220ad5d1c77a90f130ba1ff0d3910d8766",
    },
    "v2.2022": {
        "arc": "b2cdeeebfb3ff75701ccc15edb22b5c8e1153623aefc6463f9699ae8780edf15",
        "atl": "cffdb28aca195e189b16834a4f9711b90a995ea2b99d95bc6fe498049f975631",
        "ind": "00381b0542ed4e8a39c33ee071fcb2388c1e3b3fb13f76c75fc342b26f4c8a13",
        "pac": "4037f093d89ea422aa62524273ab40ca147934e34637496372e83f2e34fe9a66",
        "wor": "3d7ba5bcf59b0c1f513b6fa8140df0618d984fa7b320899e7f188dd7c6cef565",
    },
    "v2.2021": {
        "arc": "21e511e808b9cc9f5b8532bf3b1c6754bb4ad6c344adb4a498b71967a0b6d217",
        "atl": "22731e474a33d10c3efd3cc6748aafca7e1488495acefe1bbbd26b4105973a21",
        "ind": "d3c43da540e606091a981958b4ce674dbe1ef9777ffee4c90de29bcc74f010a2",
        "pac": "925cf0424f4cd1caad30cfbe57bdc19740c85e715bee06bd298893915cfc5a01",
        "wor": "8329acd8722a3c198455642f8fca29b05f460b149e178fef9e1041f2caa19453",
    },
    "v2.2020": {
        "arc": "de52e1086b61f68d46cb0142e4bcffae18b578f41c2a00bda40a8960959a94b7",
        "atl": "e927d87d873e089311ed5b747195aa150880f59559831bab27a54dcc0ff7ff69",
        "ind": "1d8dfbefb820541d9b10f73d3785dae8653e67166b94666dbb433d3ddfa4e255",
        "pac": "9a75bf66b38341117afaae947af465f8f7e4082a9f773355c1fbadf26484d544",
        "wor": "51e1000101aa61712edb9c0074289bb83c105d17ee8cea575f8e18fa05bde953",
    },
    "v2.2019": {
        "arc": "f972a835601a5b00ac5ffc5093414d5fd2a520bbc7b1c7ff0a7d343852302284",
        "atl": "6ac0826bacbaa43a9813fe18bcb84b1786efb44538b7a2d24e8a0c993ff23193",
        "ind": "aa6695b715cce7658f94911d38a344f1e835ff6bbed8f9dc1548b167983a2967",
        "pac": "88df995e272dd63db55421b911be1f99bfec4cac6f97a73e017c9e275bf29db2",
        "wor": "4637ce5eb560fe020e9fccf0370156bfe19498fc74c2e8b66dee190cc44cff63",
    },
}


def _get_paths(region, version, gpath):
    assert region in regions_full, "`region` not valid!"
    if version is None:
        version = version_latest
    version = version.lower()
    assert version in versions, "`version` not valid!"
    if gpath is None:
        gpath = os.path.join(os.path.expanduser("~"), ".glodap")
    fileregion = regions_full[region.lower()]
    filename = f"{fileregion}_{version}.mat"
    return gpath, fileregion, filename, version


def download(region="world", version=None, gpath=None, chunk_size=8192):
    """Download a GLODAP data file and save it locally, after checking that it
    has the expected checksum (SHA256).

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
    version : str or None, optional
        Which GLODAP version to download, by default `None`, in which case the
        most recent version is downloaded.  The options are:
            "v2.2023", "v2.2022", "v2.2021", "v2.2020", "v2.2019"
    gpath : str of None, optional
        Where to save the downloaded file, by default `None`, in which case the
        file is saved at "~/.glodap".
    chunk_size : int, optional
        Chunk size for streamed file download, by default 8192.
    """
    gpath, fileregion, filename, version = _get_paths(region, version, gpath)
    if not os.path.isdir(gpath):
        os.makedirs(gpath)
    url = (
        f"https://glodap.info/glodap_files/{version}/"
        + f"GLODAP{version}_{fileregion}.mat"
    )
    hasher = hashlib.new("sha256")
    checksum = checksums[version][region[:3].lower()]
    with tempfile.TemporaryDirectory() as tdir:
        temp_path = os.path.join(tdir, filename)
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(temp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
                    hasher.update(chunk)
            if hasher.hexdigest() == checksum:
                os.rename(temp_path, os.path.join(gpath, filename))
            else:
                warn("File checksum not as expected - download failed.")


def read(region="world", version=None, gpath=None):
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
    version : str or None, optional
        Which GLODAP version to import, by default `None`, in which case the
        most recent version is imported.  The options are:
            "v2.2023", "v2.2022", "v2.2021", "v2.2020", "v2.2019"
    gpath : str of None, optional
        Where to the downloaded file is or should be saved, by default `None`,
        in which case the file is imported from or saved at "~/.glodap".

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
    renamer_flags = {k: k[:-1] + "_f" for k in keys_flags}
    df = df.rename(columns=renamer_flags)
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


def arctic(version=None, gpath=None):
    """Import the latest version of the GLODAP Arctic Ocean dataset,
    downloading it first if it's not already available locally.

    Parameters
    ----------
    version : str or None, optional
        Which GLODAP version to import, by default `None`, in which case the
        most recent version is imported.  The options are:
            "v2.2023", "v2.2022", "v2.2021", "v2.2020", "v2.2019"
    gpath : str of None, optional
        Where to the downloaded file is or should be saved, by default `None`,
        in which case the file is imported from or saved at "~/.glodap".

    Returns
    -------
    pd.DataFrame
        The GLODAP Arctic Ocean dataset as a pandas DataFrame.
    """
    return read(
        region="arctic",
        version=version,
        gpath=gpath,
    )


def atlantic(version=None, gpath=None):
    """Import the latest version of the GLODAP Atlantic Ocean dataset,
    downloading it first if it's not already available locally.

    Parameters
    ----------
    version : str or None, optional
        Which GLODAP version to import, by default `None`, in which case the
        most recent version is imported.  The options are:
            "v2.2023", "v2.2022", "v2.2021", "v2.2020", "v2.2019"
    gpath : str of None, optional
        Where to the downloaded file is or should be saved, by default `None`,
        in which case the file is imported from or saved at "~/.glodap".

    Returns
    -------
    pd.DataFrame
        The GLODAP Atlantic Ocean dataset as a pandas DataFrame.
    """
    return read(
        region="atlantic",
        version=version,
        gpath=gpath,
    )


def indian(version=None, gpath=None):
    """Import the latest version of the GLODAP Indian Ocean dataset,
    downloading it first if it's not already available locally.

    Parameters
    ----------
    version : str or None, optional
        Which GLODAP version to import, by default `None`, in which case the
        most recent version is imported.  The options are:
            "v2.2023", "v2.2022", "v2.2021", "v2.2020", "v2.2019"
    gpath : str of None, optional
        Where to the downloaded file is or should be saved, by default `None`,
        in which case the file is imported from or saved at "~/.glodap".

    Returns
    -------
    pd.DataFrame
        The GLODAP Indian Ocean dataset as a pandas DataFrame.
    """
    return read(
        region="indian",
        version=version,
        gpath=gpath,
    )


def pacific(version=None, gpath=None):
    """Import the latest version of the GLODAP Pacific Ocean dataset,
    downloading it first if it's not already available locally.

    Parameters
    ----------
    version : str or None, optional
        Which GLODAP version to import, by default `None`, in which case the
        most recent version is imported.  The options are:
            "v2.2023", "v2.2022", "v2.2021", "v2.2020", "v2.2019"
    gpath : str of None, optional
        Where to the downloaded file is or should be saved, by default `None`,
        in which case the file is imported from or saved at "~/.glodap".

    Returns
    -------
    pd.DataFrame
        The GLODAP Pacific Ocean dataset as a pandas DataFrame.
    """
    return read(
        region="pacific",
        version=version,
        gpath=gpath,
    )


def world(version=None, gpath=None):
    """Import the latest version of the GLODAP Merged Master File dataset,
    downloading it first if it's not already available locally.

    Parameters
    ----------
    version : str or None, optional
        Which GLODAP version to import, by default `None`, in which case the
        most recent version is imported.  The options are:
            "v2.2023", "v2.2022", "v2.2021", "v2.2020", "v2.2019"
    gpath : str of None, optional
        Where to the downloaded file is or should be saved, by default `None`,
        in which case the file is imported from or saved at "~/.glodap".

    Returns
    -------
    pd.DataFrame
        The GLODAP Merged Master File as a pandas DataFrame dataset.
    """
    return read(
        region="world",
        version=version,
        gpath=gpath,
    )
