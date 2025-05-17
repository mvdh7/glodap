# %%
import itertools
import tempfile

import glodap


def test_response():
    with tempfile.TemporaryDirectory() as tdir:
        for region, version in itertools.product(
            glodap.regions, glodap.versions
        ):
            print(region, version)
            glodap.download(region=region, version=version, gpath=tdir)


# test_response()
