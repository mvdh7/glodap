# %%
import pandas as pd

import glodap


def test_region_names():
    # Check that the first 3 letters of each region name are unique
    regions_short = {k[:3] for k in glodap.regions}
    assert len(regions_short) == len(glodap.regions)


def test_regions_latest():
    df = glodap.arctic()
    assert isinstance(df, pd.DataFrame)
    df = glodap.atlantic()
    assert isinstance(df, pd.DataFrame)
    df = glodap.indian()
    assert isinstance(df, pd.DataFrame)
    df = glodap.pacific()
    assert isinstance(df, pd.DataFrame)
    df = glodap.world()
    assert isinstance(df, pd.DataFrame)


# test_region_names()
# test_regions_latest()
