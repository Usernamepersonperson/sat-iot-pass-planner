import pytest

from sat_iot_pass_planner.analysis import build_sets, default_start
from sat_iot_pass_planner.link import LinkParams
from sat_iot_pass_planner.passes import compute_visibility, load_sites
from sat_iot_pass_planner.tle import load_snapshot


@pytest.fixture(scope="session")
def snapshot():
    return load_snapshot()[0]


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
