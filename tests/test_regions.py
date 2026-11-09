# %%
import pandas as pd

import glodap


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


# test_regions_latest()
