# %%
import itertools
import tempfile

import pandas as pd

import glodap


def test_download_and_read():
    with tempfile.TemporaryDirectory() as tdir:
        for region, version in itertools.product(
            glodap._regions, glodap._versions
        ):
            df = glodap.read(region=region, version=version, gpath=tdir)
            assert isinstance(df, pd.DataFrame)


# test_download_and_read()
