import os
from pathlib import Path

from pyiceberg.catalog.rest import RestCatalog

from common.log.logger import get_logger

logger = get_logger("polaris")
logger.setLevel(os.environ.get("APP_LOG_LEVEL", "INFO"))

principal_creds = Path(os.getcwd()).joinpath("work", "principal.txt")
with open(principal_creds, "r") as file:
    realm, client_id, client_secret = file.readline().split(",")

logger.info(f"realm: {realm},client_id: {client_id},client_secret: {client_secret}")
# IMPORTANT!!! /api/catalog or get the suffix from your OpenCatalog instance
CATALOG_URI = os.environ.get("CATALOG_URI", "http://localhost:18181/api/catalog")
catalog_name = os.environ.get("CATALOG_NAME", "balloon-game")
database_name = os.environ.get("DATABASE_NAME", "balloon_pops")

catalog = RestCatalog(
    name=catalog_name,
    **{
        "uri": CATALOG_URI,
        "credential": f"{client_id}:{client_secret}",
        "header.content-type": "application/vnd.api+json",
        "header.X-Iceberg-Access-Delegation": "vended-credentials",
        "header.Polaris-Realm": realm,
        "warehouse": catalog_name,
        "scope": "PRINCIPAL_ROLE:ALL",
    },
)