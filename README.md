# glodap

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

The columns of the imported DataFrames are renamed so that they can be passed
directly into [PyCO2SYS v2](https://github.com/mvdh7/PyCO2SYS):

```python
import PyCO2SYS as pyco2
co2s_atlantic = pyco2.sys(data=df_atlantic, nitrite=None)
```

Note `nitrite=None` - this means PyCO2SYS will ignore the `"nitrite"` column,
which is necessary because PyCO2SYS includes the nitrite-nitrous acid
equilibrium but its equilibrium constant is valid only under lab conditions.

The columns are the same as in the original GLODAP .mat files available from [glodap.info](https://glodap.info), except:
  * The `"G2"` at the start of each parameter has been removed.
  * Flags end with `"_f"` instead of just `"f"`.
  * There is a `"datetime"` column, which combines the `"year"`, `"month"` and `"day"` but NOT the `"hour"` and `"minute"` (because some of these are missing).
  * For compatibility with PyCO2SYS:
     - `"tco2"` => `"dic"`
     - `"talk"` => `"alkalinity"`
     - `"phts25p0"` => `"ph_lab"`
     - `"phtsinsitutp"` => `"ph_insitu"`
    
    Therefore when passing the DataFrame directly to PyCO2SYS as in the example
    above, the system will be solved from DIC and alkalinity, not pH.

The functions `download` and `read` can also be used for finer control, such as
specifying a particular GLODAP version rather than using the latest one.  See
their function docstrings for more information.
