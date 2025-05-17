# %%
import itertools

import glodap


def test_responses():
    for region, version in itertools.product(glodap.regions, glodap.versions):
        status = glodap.download(
            region=region, version=version, do_download=False
        )
        assert status == 200, f"Failed on {region} {version}"


# test_responses()
