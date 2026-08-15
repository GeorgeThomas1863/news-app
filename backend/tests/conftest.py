import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest
import pytest_asyncio
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app import db
from app.pipeline import runner

TEST_DB_NAME = "news_app_test"
DEFAULT_URI = "mongodb://localhost:27017"
SCRATCH_PORT = 27018
SCRATCH_URI = f"mongodb://localhost:{SCRATCH_PORT}"
WINDOWS_MONGOD_DIR = r"C:\Program Files\MongoDB\Server"


@pytest.fixture(autouse=True)
def reset_pipeline_flags():
    """Paused/stop state is module-level; never let it leak between tests."""
    yield
    runner.resume()


@pytest.fixture(scope="session")
def test_mongo_uri():
    """Explicit TEST_MONGO_URI wins; else the local default; else a scratch mongod we own."""
    explicit = os.environ.get("TEST_MONGO_URI")
    if explicit:
        yield explicit
        return

    if can_use_mongo(DEFAULT_URI):
        yield DEFAULT_URI
        return

    process, data_dir = start_scratch_mongod()
    yield SCRATCH_URI
    stop_scratch_mongod(process, data_dir)


@pytest_asyncio.fixture
async def test_db(test_mongo_uri):
    """Real local Mongo, dedicated test database, dropped before and after each test."""
    await db.init_db(test_mongo_uri, TEST_DB_NAME)
    await db.client.drop_database(TEST_DB_NAME)
    await db.ensure_indexes()
    yield db
    await db.client.drop_database(TEST_DB_NAME)
    await db.close_db()


# --- scratch mongod (used when the default instance is down or requires auth)


def can_use_mongo(uri):
    """True when the test database is fully usable there (reachable, no auth wall)."""
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=500)
        client[TEST_DB_NAME].list_collection_names()
        client.close()
        return True
    except PyMongoError:
        return False


def start_scratch_mongod():
    mongod = find_mongod_binary()
    if mongod is None:
        pytest.exit(
            f"{DEFAULT_URI} is unusable (down or requires auth) and no mongod binary "
            "was found to start a scratch instance. Set TEST_MONGO_URI to a usable instance."
        )

    data_dir = tempfile.mkdtemp(prefix="news_app_test_mongo_")
    process = subprocess.Popen(
        [
            mongod,
            "--port", str(SCRATCH_PORT),
            "--dbpath", data_dir,
            "--bind_ip", "127.0.0.1",
            "--logpath", str(Path(data_dir) / "mongod.log"),
        ]
    )
    wait_for_scratch_mongod(process, data_dir)
    return process, data_dir


def find_mongod_binary():
    on_path = shutil.which("mongod")
    if on_path:
        return on_path
    installs = sorted(Path(WINDOWS_MONGOD_DIR).glob("*/bin/mongod.exe"), reverse=True)
    return str(installs[0]) if installs else None


def wait_for_scratch_mongod(process, data_dir):
    for _ in range(40):
        if can_use_mongo(SCRATCH_URI):
            return
        time.sleep(0.25)
    process.terminate()
    pytest.exit(f"Scratch mongod on port {SCRATCH_PORT} never became ready — see {data_dir}\\mongod.log")


def stop_scratch_mongod(process, data_dir):
    process.terminate()
    process.wait(timeout=10)
    shutil.rmtree(data_dir, ignore_errors=True)
