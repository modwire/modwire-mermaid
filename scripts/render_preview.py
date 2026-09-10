from pathlib import Path

from mermaiden import Application
from tests.fixtures.catalog import FixtureCatalog

output = Path(".dev/preview/index.html")
with Application.create() as application:
    application.write_preview(FixtureCatalog(application).render(), output)

print(output)
