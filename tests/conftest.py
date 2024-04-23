import shutil

from tests.settings import STORAGES


def pytest_sessionfinish(session, exitstatus):
    path = STORAGES["default"]["OPTIONS"]["location"]
    shutil.rmtree(path)
