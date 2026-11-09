# %%
import glodap


def test_version_latest():
    assert glodap.version_latest in glodap.versions


def test_checksum_versions_and_regions():
    for v, rs in glodap._checksums.items():
        assert v in glodap.versions
        for r in rs:
            assert r in glodap._regions
        for r in glodap._regions:
            assert r in rs
    for v in glodap.versions:
        assert v in glodap._checksums


# test_version_latest()
# test_checksum_versions_and_regions()
