import os
from pathlib import Path

# Set test environment variables before any application code is imported
os.environ["VALID_PASSCODE"] = "test-passcode"
os.environ["DATABASE_URL"] = f"sqlite:///{Path(__file__).with_name('test.db')}"
os.environ["VERTEX_PROJECT"] = "test-project"
