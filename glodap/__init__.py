"""
GLODAP
======
Download Global Ocean Data Analysis Project (https://glodap.info)
version 2 and 3 datasets and import them as pandas DataFrames.

FUNCTIONS
---------
The functions `arctic`, `atlantic`, `indian`, `pacific` and `world`
import the latest version (by default) of the GLODAP dataset for the
corresponding region, first downloading the file if it's not already
saved locally.  For example:

  >>> import glodap
  >>> df_atlantic = glodap.atlantic()

Function kwargs
---------------
All functions (`arctic`, `atlantic`, `indian`, `pacific` and `world`)
have the same kwargs:

version : str or None, optional
    Which GLODAP version to download.  All of the options are listed in
    `glodap.versions`.  If `None`, then the most recent version is used,
    which is given by `glodap.version_latest`.
gpath : str or pathlib.Path or None, optional
    Where to look for the GLODAP file and to download it to if not
    found there.  If `None`, then `"~/.glodap"` is used.

When files are missing, the .mat (v2) or zipped CSV (v3) files from the
GEOMAR mirrors (i.e., from https://glodap.info) are downloaded.  After
download, the SHA256 checksum of each file is verified and the download
is rejected in case of mismatch.

Function return values
----------------------
The requested GLODAP dataset is returned as a pandas DataFrame.

The columns are the same as in the original GLODAP files, except:
  - v2 datasets only: the "G2" at the start of each column name has been
    removed.
  - Flags end with `"_f"` instead of just `"f"`.
  - A `"datetime"` column has been added, which combines the `"year"`,
    `"month"` and `"day"`, but NOT the `"hour"` and `"minute"` (because
    some of these are missing).

ATTRIBUTES
----------
versions : list[str]
    All possible GLODAP dataset version strings.
version_latest : str
    The current latest version, which will be used if the `version`
    kwarg is not provided.
"""

from pathlib import Path
from typing import NamedTuple
from urllib.parse import quote

import numpy as np
import pandas as pd
import pooch
from scipy.io import loadmat


# Package metadata
__author__ = "Matthew P. Humphreys"
__version__ = "0.5"
__all__ = [
    "arctic",
    "atlantic",
    "indian",
    "pacific",
    "version_latest",
    "versions",
    "world",
]

# GLODAP metadata
version_latest = "v3.2026"
versions = [
    "v3.2026",
    "v2.2023",
    "v2.2022",
    "v2.2021",
    "v2.2020",
    "v2.2019",
    "v2.2016",
]
_regions = {
    "arctic": "Arctic_Ocean",
    "atlantic": "Atlantic_Ocean",
    "indian": "Indian_Ocean",
    "pacific": "Pacific_Ocean",
    "world": "Merged_Master_File",
}
_checksums = {
    "v3.2026": {
        "arctic": "03dfcf59525931065247e142439d97c0ed88d8f572e87df919476deebdc57d5c",
        "atlantic": "a4577bbb676c30327b185fc5bf0ddc0e302464d5332b6d630922faf536dbe68c",
        "indian": "79d655bd203e4579007b7224fc53b87ee8a5d70bb733550f0acac260a6baa0d8",
        "pacific": "1a5afbb6be199773e00772ca3b1b84241dfc52a591b3f6b85786180f5711a9b4",
        "world": "214aeb49c618474bf92622a37d2795a10160954ab49a94f9052cff1dd41947fd",
    },
    "v2.2023": {
        "arctic": "a998a8d99db84e9357b21a7e345bbfde62eae77870e651119b4c1929a2f1e2fd",
        "atlantic": "a3ff7bc4f4ff3a1b0f540886a0eb7c9b3ec52aa4eae2dea57d47ae61f56da56f",
        "indian": "8c9c21d4af9db506b09fdec79e2a311c2dbbf41b8fc4e6a7a855d1d50b3ccb51",
        "pacific": "9891160dba6211d2f13923171564a06bbea34cda799f3091148061c32fc6070c",
        "world": "002881fa71923d15c1bd5aca3b99bc220ad5d1c77a90f130ba1ff0d3910d8766",
    },
    "v2.2022": {
        "arctic": "b2cdeeebfb3ff75701ccc15edb22b5c8e1153623aefc6463f9699ae8780edf15",
        "atlantic": "cffdb28aca195e189b16834a4f9711b90a995ea2b99d95bc6fe498049f975631",
        "indian": "00381b0542ed4e8a39c33ee071fcb2388c1e3b3fb13f76c75fc342b26f4c8a13",
        "pacific": "4037f093d89ea422aa62524273ab40ca147934e34637496372e83f2e34fe9a66",
        "world": "3d7ba5bcf59b0c1f513b6fa8140df0618d984fa7b320899e7f188dd7c6cef565",
    },
    "v2.2021": {
        "arctic": "21e511e808b9cc9f5b8532bf3b1c6754bb4ad6c344adb4a498b71967a0b6d217",
        "atlantic": "22731e474a33d10c3efd3cc6748aafca7e1488495acefe1bbbd26b4105973a21",
        "indian": "d3c43da540e606091a981958b4ce674dbe1ef9777ffee4c90de29bcc74f010a2",
        "pacific": "925cf0424f4cd1caad30cfbe57bdc19740c85e715bee06bd298893915cfc5a01",
        "world": "8329acd8722a3c198455642f8fca29b05f460b149e178fef9e1041f2caa19453",
    },
    "v2.2020": {
        "arctic": "de52e1086b61f68d46cb0142e4bcffae18b578f41c2a00bda40a8960959a94b7",
        "atlantic": "e927d87d873e089311ed5b747195aa150880f59559831bab27a54dcc0ff7ff69",
        "indian": "1d8dfbefb820541d9b10f73d3785dae8653e67166b94666dbb433d3ddfa4e255",
        "pacific": "9a75bf66b38341117afaae947af465f8f7e4082a9f773355c1fbadf26484d544",
        "world": "51e1000101aa61712edb9c0074289bb83c105d17ee8cea575f8e18fa05bde953",
    },
    "v2.2019": {
        "arctic": "f972a835601a5b00ac5ffc5093414d5fd2a520bbc7b1c7ff0a7d343852302284",
        "atlantic": "6ac0826bacbaa43a9813fe18bcb84b1786efb44538b7a2d24e8a0c993ff23193",
        "indian": "aa6695b715cce7658f94911d38a344f1e835ff6bbed8f9dc1548b167983a2967",
        "pacific": "88df995e272dd63db55421b911be1f99bfec4cac6f97a73e017c9e275bf29db2",
        "world": "4637ce5eb560fe020e9fccf0370156bfe19498fc74c2e8b66dee190cc44cff63",
    },
    "v2.2016": {
        "arctic": "f2214409e0526052903da2427f3f8c6fd433b1759ba2a1be3a61181b4b0d04b7",
        "atlantic": "fb26a86ca1135a0afc94157ba7963bc1cb8138523bcba36360595641175f8da1",
        "indian": "ba162aa6f1fa7209f586e503581d3cc05cdffbfa6f72bdc535824f7a78d694f9",
        "pacific": "0d1666de27ad6853533651027459d2525f75c6681d540f129df705b018d3c931",
        "world": "aa202e330d5e77b98d0062e40a40665b8397b83ebbfa00424532139c53814f5e",
    },
}

_keys_flags = [
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
_renamer_flags = {k: k[:-1] + "_f" for k in _keys_flags}


class ParsedInputs(NamedTuple):
    gpath: Path
    region: str
    fileregion: str
    filename: str
    version: str


def _parse_inputs(
    region: str,
    version: str | None,
    gpath: str | Path | None,
) -> ParsedInputs:
    region = region.lower()
    if region not in _regions:
        raise ValueError("`region` not valid!")
    if version is None:
        version = version_latest
    version = version.lower()
    if version not in versions:
        raise ValueError("`version` not valid!")
    if gpath is None:
        gpath = "~/.glodap"
    gpath = Path(gpath).expanduser()
    fileregion = _regions[region]
    if version.startswith("v2"):
        filename = f"{fileregion}_{version}.mat"
    elif version.startswith("v3"):
        filename = f"{fileregion}_{version}.csv.zip"
    return ParsedInputs(gpath, region, fileregion, filename, version)


def _download(
    region: str = "world",
    version: str | None = None,
    gpath: str | Path | None = None,
) -> None:
    """Download a GLODAP data file and save it locally, after checking
    that it has the expected checksum (SHA256).

    Parameters
    ----------
    region : str, optional
        Which GLODAP region to download, by default "world", which is
        the Merged Master File.  The options are:
            "arctic"    Arctic Ocean
            "atlantic"  Atlantic Ocean
            "indian"    Indian Ocean
            "pacific"   Pacific Ocean
            "world"     Merged Master File
    version : str or None, optional
        Which GLODAP version to download, by default `None`, in which
        case the most recent version is downloaded.  The options are
        given in `glodap.versions`.
    gpath : str or None, optional
        Where to save the downloaded file, by default `None`, in which
        case the file is saved at "~/.glodap".
    """
    gpath, region, fileregion, filename, version = _parse_inputs(
        region, version, gpath
    )
    gpath.mkdir(parents=True, exist_ok=True)
    if version == "v2.2016":
        fr = fileregion.replace("_", " ")
        url = f"{version}/GLODAPv2 {fr}.mat"
    elif version.startswith("v2"):
        url = f"{version}/GLODAP{version}_{fileregion}.mat"
    elif version.startswith("v3"):
        url = f"v3/GLODAPv3_{fileregion}.csv.zip"
    checksum = _checksums[version][region]
    pooch.retrieve(
        "https://glodap.info/glodap_files/" + quote(url, safe="/"),
        known_hash=f"sha256:{checksum}",
        fname=filename,
        path=gpath,
    )


def _read(
    region: str = "world",
    version: str | None = None,
    gpath: str | Path | None = None,
) -> pd.DataFrame:
    """Import a GLODAP data file as a pandas DataFrame, downloading it
    first if it's not already available locally.

    Parameters
    ----------
    region : str, optional
        Which GLODAP region to import, by default "world", which is the
        Merged Master File.  The options are:
            "arctic"    Arctic Ocean
            "atlantic"  Atlantic Ocean
            "indian"    Indian Ocean
            "pacific"   Pacific Ocean
            "world"     Merged Master File
    version : str or None, optional
        Which GLODAP version to import, by default `None`, in which case
        the most recent version is imported.  The options are given in
        `glodap.versions`.
    gpath : str or None, optional
        Where the downloaded file is or should be saved, by default
        `None`, in which case the file is imported from or saved at
        "~/.glodap".

    Returns
    -------
    pd.DataFrame
        The GLODAP dataset as a pandas DataFrame.
    """
    gpath, region, _, filename, version = _parse_inputs(region, version, gpath)
    # _download checks if the file is already there before downloading,
    # so it's fine to always run it here.  It's also useful to have in
    # because it checks the checksum of already-downloaded files.
    _download(region=region, version=version, gpath=gpath)
    if version.startswith("v2"):
        df = loadmat(gpath / filename)
        df = pd.DataFrame(
            {
                k[2:]: [w[0][0] for w in v] if v.dtype == object else v.ravel()
                for k, v in df.items()
                if k.startswith("G2")
            }
        )
    elif version.startswith("v3"):
        df = pd.read_csv(
            gpath / filename,
            compression="zip",
            dtype={
                "expocode": str,
                "ph_scale": str,
            },
            na_values=[-9999, "-9999"],
        )
    # Convert columns that should be integers into integers
    # Add missing flags in v2.2016
    if version == "v2.2016" and region in ["indian", "world"]:
        ks = [k for k in _keys_flags if k in df]
        df[ks] = df[ks].fillna(9)
    # Can't convert "cast", "hour" or "minute" to integers because they
    # have missing values
    dtypes = {
        k: np.uint8  # 0 to 255
        for k in _keys_flags + ["region", "month", "day"]
        if k in df
    }
    dtypes["year"] = np.uint16  # 0 to 65535
    dtypes["cruise"] = int
    dtypes["station"] = int
    df = df.astype(dtypes)
    # Rename flag columns
    df = df.rename(columns=_renamer_flags)
    # Correct fatal datetime errors in v2.2016
    if version == "v2.2016":
        if region in ["indian", "world"]:
            L = (df.cruise == 696) & (df.station == 15537)
            df.loc[L, "month"] = 12
            df.loc[L, "day"] = 1
        if region in ["pacific", "world"]:
            L = (df.cruise == 270) & (df.station == 113)
            df.loc[L, "month"] = 4
            df.loc[L, "day"] = 30
    df._consolidate_inplace()  # suppresses 'highly fragmented DataFrame' warning
    # Calculate datetime for convenience - but exclude hour and minute,
    # because some are missing
    df["datetime"] = pd.to_datetime(df[["year", "month", "day"]])
    return df


def arctic(
    version: str | None = None,
    gpath: str | Path | None = None,
) -> pd.DataFrame:
    """Import the latest version of the GLODAP Arctic Ocean dataset,
    downloading it first if it's not already available locally.

    See the `glodap` module docstring for info on the optional kwargs.
    """
    return _read(region="arctic", version=version, gpath=gpath)


def atlantic(
    version: str | None = None,
    gpath: str | Path | None = None,
) -> pd.DataFrame:
    """Import the latest version of the GLODAP Atlantic Ocean dataset,
    downloading it first if it's not already available locally.

    See the `glodap` module docstring for info on the optional kwargs.
    """
    return _read(region="atlantic", version=version, gpath=gpath)


def indian(
    version: str | None = None,
    gpath: str | Path | None = None,
) -> pd.DataFrame:
    """Import the latest version of the GLODAP Indian Ocean dataset,
    downloading it first if it's not already available locally.

    See the `glodap` module docstring for info on the optional kwargs.
    """
    return _read(region="indian", version=version, gpath=gpath)


def pacific(
    version: str | None = None,
    gpath: str | Path | None = None,
) -> pd.DataFrame:
    """Import the latest version of the GLODAP Pacific Ocean dataset,
    downloading it first if it's not already available locally.

    See the `glodap` module docstring for info on the optional kwargs.
    """
    return _read(region="pacific", version=version, gpath=gpath)


def world(
    version: str | None = None,
    gpath: str | Path | None = None,
) -> pd.DataFrame:
    """Import the latest version of the GLODAP Merged Master File
    dataset, downloading it first if it's not already available locally.

    See the `glodap` module docstring for info on the optional kwargs.
    """
    return _read(region="world", version=version, gpath=gpath)
