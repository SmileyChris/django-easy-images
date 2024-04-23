import os
import shutil

from tests.settings import STORAGES


def pytest_sessionfinish(session, exitstatus):
    path = STORAGES["default"]["OPTIONS"]["location"]
    if os.path.exists(path):
        shutil.rmtree(path)
