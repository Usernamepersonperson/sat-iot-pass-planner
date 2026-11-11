import socket

import pytest

from sat_iot_pass_planner.analysis import build_sets, default_start
from sat_iot_pass_planner.link import LinkParams
from sat_iot_pass_planner.passes import compute_visibility, load_sites
from sat_iot_pass_planner.synthetic import load_synthetic


@pytest.fixture(scope="session", autouse=True)
def no_network(tmp_path_factory):
    """Tests never download: any socket connect fails, and the cache points at an empty directory."""

    def refuse(*_a, **_k):
        raise AssertionError("tests must not use the network")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(socket.socket, "connect", refuse)
        mp.setenv("SAT_IOT_CACHE_DIR", str(tmp_path_factory.mktemp("empty_cache")))
        yield


@pytest.fixture(scope="session")
def snapshot():
    """Synthetic element sets (made-up orbits, valid TLE layout and checksums)."""
    return load_synthetic()[0]


@pytest.fixture(scope="session")
def sites():
    return load_sites()


@pytest.fixture(scope="session")
def sso_set(snapshot):
    return build_sets(snapshot, {"sso": 24})["sso"]


@pytest.fixture(scope="session")
def start(sso_set):
    return default_start(sso_set)


@pytest.fixture(scope="session")
def vis_valley(sso_set, sites, start):
    return compute_visibility(sso_set, sites["lauterbrunnen_valley"], start, 2.0, LinkParams())


@pytest.fixture(scope="session")
def vis_ridge(sso_set, sites, start):
    return compute_visibility(sso_set, sites["schilthorn_ridge"], start, 2.0, LinkParams())
