import pytest_asyncio

from app import db

TEST_MONGO_URI = "mongodb://localhost:27017"
TEST_DB_NAME = "news_app_test"


@pytest_asyncio.fixture
async def test_db():
    """Real local Mongo, dedicated test database, dropped before and after each test."""
    await db.init_db(TEST_MONGO_URI, TEST_DB_NAME)
    await db.client.drop_database(TEST_DB_NAME)
    await db.ensure_indexes()
    yield db
    await db.client.drop_database(TEST_DB_NAME)
    await db.close_db()
