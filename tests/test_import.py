# %%
import pandas as pd

import glodap


def test_import():
    df = glodap.arctic(gpath="tests/data")
    assert isinstance(df, pd.DataFrame)


# test_import()
