# glodap

[![Tests](https://github.com/mvdh7/glodap/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/mvdh7/glodap/actions)
[![pypi badge](https://img.shields.io/pypi/v/glodap.svg?style=popout)](https://pypi.org/project/glodap/)
[![Conda Version](https://img.shields.io/conda/vn/conda-forge/glodap.svg)](https://anaconda.org/conda-forge/glodap)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Download [GLODAP](https://glodap.info) datasets and import them as pandas DataFrames.

## Install

    pip install glodap
    conda install conda-forge::glodap

## Use

The functions `arctic`, `atlantic`, `indian`, `pacific` and `world` import the latest version of the GLODAP dataset for the corresponding region, first downloading the file if it's not already saved locally.  For example:

```python
import glodap
df_atlantic = glodap.atlantic()
```

Files are saved by default at `"~/.glodap"`, but this can be controlled with the
kwarg `gpath`.  See the function docstrings for more information.

The columns of the imported DataFrames can be passed
directly into [PyCO2SYS v2](https://mvdh.xyz/PyCO2SYS):

```python
import PyCO2SYS as pyco2
co2s_atlantic = pyco2.sys(data=df_atlantic.drop(columns="fco2"), nitrite=0)
```

Note `nitrite=0` - this means PyCO2SYS will ignore the `"nitrite"` column,
which is necessary because while PyCO2SYS includes the nitrite-nitrous acid
equilibrium, its equilibrium constant is valid only under lab conditions.

Because of how the columns are named, and because we dropped the `"fco2"` column, when passing the DataFrame directly to
PyCO2SYS as above, the system will be solved from DIC and alkalinity, not pH nor fCO<sub>2</sub>.

The columns are the same as in the original GLODAP .mat files available from [glodap.info](https://glodap.info), except:
  * The `"G2"` at the start of each parameter has been removed.
  * Flags end with `"_f"` instead of just `"f"`.
  * There is a `"datetime"` column, which combines the `"year"`, `"month"` and `"day"` but NOT the `"hour"` and `"minute"` (because some of these are missing).

The functions `download` and `read` can also be used for finer control, such as
specifying a particular GLODAP version rather than using the latest one.  See
their function docstrings for more information.

The .mat files from the GEOMAR mirrors are downloaded, and the SHA256 checksum
of each downloaded file is checked before the file is written to disk.
