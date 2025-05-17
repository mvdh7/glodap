# %%
import glodap


def test_region_names():
    # Check that the first 3 letters of each region name are unique
    regions_short = {k[:3] for k in glodap.regions}
    assert len(regions_short) == len(glodap.regions)


# test_region_names()
