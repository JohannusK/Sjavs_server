import os

# Prevent globally installed pytest plugins from interfering with the local test run.
os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
