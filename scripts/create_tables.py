#!/usr/bin/env python3
# %% [markdown]
# # Apache Iceberg Workbook
#
# This notebook allows to work with Iceberg tables using PyIceberg lib. This workbook helps you to
# - [x] Connect with Polaris REST Catalog
# - [x] Create Iceberg Tables
#

# %% [markdown]
# ## Imports
#

# %%
import os
from pathlib import Path

# %% [markdown]
# ## PyIceberg Version
# %%
import pyiceberg
from pyiceberg.catalog.rest import RestCatalog
from pyiceberg.exceptions import NamespaceAlreadyExistsError, TableAlreadyExistsError
from pyiceberg.partitioning import (
    PartitionField,
    PartitionSpec,
)
from pyiceberg.schema import Schema
from pyiceberg.table.sorting import (
    NullOrder,
    SortDirection,
    SortField,
    SortOrder,
)
from pyiceberg.transforms import (
    DayTransform,
    HourTransform,
    IdentityTransform,
    VoidTransform,
)
from pyiceberg.types import (
    DecimalType,
    LongType,
    NestedField,
    StringType,
    TimestamptzType,
)

print(f"Using PyIceberg version: {pyiceberg.__version__}\n")

# %% [markdown]
# ## Retrieve Principal Credentials
#
# As part of the catalog setup script, the Principal(`super_user`) credentials are stored in `$PROJECT_HOME/work/principal.txt`, let us retrieve it for further operations.
#

# %%
principal_cred_file = Path(os.getcwd()).parent.joinpath(
    os.getenv("PROJECT_HOME"),
    "work",
    "principal.txt",
)
with open(principal_cred_file, "r") as file:
    realm, client_id, client_secret = file.readline().split(",")

# %% [markdown]
# ## Define Variables
#
# Let us define some variables for us across the notebook
#

# %%
POLARIS_BASE_URI = "http://localhost:18181"
# IMPORTANT!!! /api/catalog or get the prefix from your OpenCatalog instance
CATALOG_URI = f"{POLARIS_BASE_URI}/api/catalog"
OAUTH2_SERVER_URI = f"{POLARIS_BASE_URI}/api/catalog/v1/oauth/tokens"
catalog_name = "balloon-game"
# database
namespace = "balloon_pops"

# %% [markdown]
# ## Working with Catalog
#
# Let us retrieve the catalog `balloon-game` that we created earlier using the `catalog_setup.yml` script.
#

# %%
catalog = RestCatalog(
    name=catalog_name,
    **{
        "uri": CATALOG_URI,
        "credential": f"{client_id}:{client_secret}",
        "header.content-type": "application/vnd.api+json",
        "header.X-Iceberg-Access-Delegation": "vended-credentials",
        "header.Polaris-Realm": realm,
        "oauth2-server-uri": OAUTH2_SERVER_URI,
        "warehouse": catalog_name,
        "scope": "PRINCIPAL_ROLE:ALL",
    },
)

# %% [markdown]
# ### Create Database(Namespace)
#
# Create a new database named `balllon_pops`
#

# %%
try:
    catalog.create_namespace(namespace)
except NamespaceAlreadyExistsError:
    print(f"Namespace '{namespace}' already exists")
except Exception as e:
    print(e)

# %% [markdown]
# ## Create Tables
#

# %% [markdown]
# #### Leaderboard
#

# %%
try:
    ## Create leaderboard Table
    leaderboard_table_id = f"{namespace}.leaderboard"
    # since its demo, dropping and creating it for sanity
    # catalog.drop_table(leaderboard_table_id)
    ## Schema
    leaderboard_schema = Schema(
        NestedField(
            field_id=1,
            name="player",
            type=StringType(),
            required=True,
        ),
        NestedField(
            field_id=2,
            name="total_score",
            type=LongType(),
            required=True,
        ),
        NestedField(
            field_id=3,
            name="bonus_hits",
            type=LongType(),
            required=True,
        ),
        NestedField(
            field_id=4,
            name="event_ts",
            type=TimestamptzType(),
            required=True,
        ),
    )
    ## Partition Specification
    partition_fields = [
        PartitionField(
            source_id=4,
            field_id=1001,
            transform=DayTransform(),
            name="datetime_day",
        ),
        PartitionField(
            source_id=1,
            field_id=1002,
            transform=IdentityTransform(),
            name="by_player",
        ),
    ]
    leaderboard_partition_spec = PartitionSpec(*partition_fields)
    ## Sort Specification
    order_fields = [
        SortField(
            source_id=2,
            direction=SortDirection.DESC,
            null_order=NullOrder.NULLS_LAST,
            transform=VoidTransform(),
        ),
        SortField(
            source_id=3,
            direction=SortDirection.DESC,
            null_order=NullOrder.NULLS_LAST,
            transform=VoidTransform(),
        ),
    ]
    sort_order = SortOrder(*order_fields)

    leaderboard_table = catalog.create_table(
        identifier=leaderboard_table_id,
        schema=leaderboard_schema,
        partition_spec=leaderboard_partition_spec,
        sort_order=sort_order,
        properties={
            "format-version": "2",  # Required for merge-on-read
            # TODO: enable upsert  https://github.com/apache/iceberg/issues/6568
            # "write.delete.mode": "merge-on-read",  # required for upserts
            # "write.update.mode": "merge-on-read",  # required for upserts
            # "write.merge.mode": "merge-on-read",  # required for upserts
        },
    )
    print(f"Created Table {leaderboard_table_id} successfully,\n{leaderboard_table}")
except TableAlreadyExistsError:
    print(f"Table '{leaderboard_table_id}' already exists")

# %% [markdown]
# #### Balloon Color Stats

# %%
## Create balloon_color_stats table
try:
    balloon_color_stats_table_id = f"{namespace}.balloon_color_stats"
    # since its demo, dropping and creating it for sanity
    # catalog.drop_table(balloon_color_stats_table_id)
    ## Schema
    balloon_color_stats_schema = Schema(
        NestedField(
            field_id=1,
            name="player",
            type=StringType(),
            required=True,
        ),
        NestedField(
            field_id=2,
            name="balloon_color",
            type=StringType(),
            required=True,
        ),
        NestedField(
            field_id=3,
            name="balloon_pops",
            type=LongType(),
            required=True,
        ),
        NestedField(
            field_id=4,
            name="points_by_color",
            type=LongType(),
            required=True,
        ),
        NestedField(
            field_id=5,
            name="bonus_hits",
            type=LongType(),
            required=True,
        ),
        NestedField(
            field_id=6,
            name="event_ts",
            type=TimestamptzType(),
            required=True,
        ),
    )
    ## Partition Specification
    partition_fields = [
        PartitionField(
            source_id=6,
            field_id=1001,
            transform=DayTransform(),
            name="datetime_day",
        ),
        PartitionField(
            source_id=2,
            field_id=1002,
            transform=IdentityTransform(),
            name="by_balloon_color",
        ),
        PartitionField(
            source_id=1,
            field_id=1003,
            transform=IdentityTransform(),
            name="by_player",
        ),
    ]
    balloon_color_stats_partition_spec = PartitionSpec(*partition_fields)
    ## Sort Specification
    order_fields = [
        SortField(
            source_id=4,
            direction=SortDirection.DESC,
            null_order=NullOrder.NULLS_LAST,
            transform=VoidTransform(),
        ),
        SortField(
            source_id=3,
            direction=SortDirection.DESC,
            null_order=NullOrder.NULLS_LAST,
            transform=VoidTransform(),
        ),
    ]
    sort_order = SortOrder(*order_fields)
    ## Create Table
    balloon_color_stats_table = catalog.create_table(
        identifier=balloon_color_stats_table_id,
        schema=balloon_color_stats_schema,
        partition_spec=balloon_color_stats_partition_spec,
        sort_order=sort_order,
        properties={
            "format-version": "2",  # Required for merge-on-read
            # TODO: enable upsert  https://github.com/apache/iceberg/issues/6568
            # "write.delete.mode": "merge-on-read",  # required for upserts
            # "write.update.mode": "merge-on-read",  # required for upserts
            # "write.merge.mode": "merge-on-read",  # required for upserts
        },
    )
    print(
        f"Created Table {balloon_color_stats_table_id} successfully,\n{balloon_color_stats_table}"
    )
except TableAlreadyExistsError:
    print(f"Table '{balloon_color_stats_table_id}' already exists")

# %% [markdown]
# ### Timseries

# %% [markdown]
# #### Realtime Scores

# %%
## Create realtime_scores table
try:
    realtime_scores_tbl_id = f"{namespace}.realtime_scores"
    # since its demo, dropping and creating it for sanity
    # catalog.drop_table(realtime_scores_tbl_id)
    ## Schema
    realtime_scores_schema = Schema(
        NestedField(
            field_id=1,
            name="player",
            type=StringType(),
            required=True,
        ),
        NestedField(
            field_id=2,
            name="total_score",
            type=LongType(),
            required=True,
        ),
        NestedField(
            field_id=3,
            name="window_start",
            type=TimestamptzType(),
            required=True,
        ),
        NestedField(
            field_id=4,
            name="window_end",
            type=TimestamptzType(),
            required=True,
        ),
    )

    realtime_scores_table = catalog.create_table(
        identifier=realtime_scores_tbl_id,
        schema=realtime_scores_schema,
        partition_spec=PartitionSpec(
            PartitionField(
                source_id=3,
                field_id=1001,
                name="by_window_start_hour",
                transform=HourTransform(),
            ),
        ),
        properties={
            "format-version": "2",
        },
    )
    print(
        f"Created Table {realtime_scores_tbl_id} successfully,\n{realtime_scores_table}"
    )
except TableAlreadyExistsError:
    print(f"Table '{realtime_scores_tbl_id}' already exists")

# %% [markdown]
# #### Balloon Colored Pops

# %%
## Create balloon_colored_pops table
try:
    balloon_colored_pops_tbl_id = f"{namespace}.balloon_colored_pops"
    # catalog.drop_table(balloon_colored_pops_tbl_id)
    ## Schema
    balloon_colored_pops_schema = Schema(
        NestedField(
            field_id=1,
            name="player",
            type=StringType(),
            required=True,
        ),
        NestedField(
            field_id=2,
            name="balloon_color",
            type=StringType(),
            required=True,
        ),
        NestedField(
            field_id=3,
            name="balloon_pops",
            type=LongType(),
            required=True,
        ),
        NestedField(
            field_id=4,
            name="points_by_color",
            type=LongType(),
            required=True,
        ),
        NestedField(
            field_id=5,
            name="bonus_hits",
            type=LongType(),
            required=True,
        ),
        NestedField(
            field_id=6,
            name="window_start",
            type=TimestamptzType(),
            required=True,
        ),
        NestedField(
            field_id=7,
            name="window_end",
            type=TimestamptzType(),
            required=True,
        ),
    )

    partition_fields = [
        PartitionField(
            source_id=6,  # window_start
            field_id=1001,
            name="by_window_start_hour",
            transform=HourTransform(),
        ),
        PartitionField(
            source_id=1,  # player field
            field_id=1002,
            name="by_player",
            transform=IdentityTransform(),
        ),
    ]
    balloon_colored_pops_table = catalog.create_table(
        identifier=balloon_colored_pops_tbl_id,
        schema=balloon_colored_pops_schema,
        partition_spec=PartitionSpec(*partition_fields),
        sort_order=SortOrder(
            SortField(
                source_id=2,  # balloon_color field
                transform=IdentityTransform(),
                direction=SortDirection.ASC,
                null_order=NullOrder.NULLS_LAST,
            ),
        ),
        properties={
            "format-version": "2",
        },
    )
    print(
        f"Created Table {balloon_colored_pops_tbl_id} successfully,\n{balloon_colored_pops_table}"
    )
except TableAlreadyExistsError:
    print(f"Table '{balloon_colored_pops_tbl_id}' already exists")

# %% [markdown]
# #### Color Performance Trends

# %%
## Create color_performance_trends table
try:
    color_performance_trends_pops_tbl_id = f"{namespace}.color_performance_trends"
    # catalog.drop_table(color_performance_trends_pops_tbl_id)
    # ## Schema
    color_performance_trends_pops_schema = Schema(
        NestedField(
            field_id=1,
            name="balloon_color",
            type=StringType(),
            required=True,
        ),
        NestedField(
            field_id=2,
            name="avg_score_per_pop",
            type=DecimalType(28, 10),
            required=True,
        ),
        NestedField(
            field_id=3,
            name="total_pops",
            type=LongType(),
            required=True,
        ),
        NestedField(
            field_id=4,
            name="window_start",
            type=TimestamptzType(),
            required=True,
        ),
        NestedField(
            field_id=5,
            name="window_end",
            type=TimestamptzType(),
            required=True,
        ),
    )

    partition_fields = [
        PartitionField(
            source_id=4,  # window_start
            field_id=1001,
            name="by_window_start_hour",
            transform=HourTransform(),
        ),
        PartitionField(
            source_id=1,  # balloon_color field
            field_id=1002,
            name="by_balloon_color",
            transform=IdentityTransform(),
        ),
    ]
    color_performance_trends_pops_table = catalog.create_table(
        identifier=color_performance_trends_pops_tbl_id,
        schema=color_performance_trends_pops_schema,
        partition_spec=PartitionSpec(*partition_fields),
        sort_order=SortOrder(
            SortField(
                source_id=1,  # balloon_color field
                transform=IdentityTransform(),
                direction=SortDirection.ASC,
                null_order=NullOrder.NULLS_LAST,
            ),
        ),
        properties={
            "format-version": "2",
        },
    )
    print(
        f"Created Table {color_performance_trends_pops_tbl_id} successfully, {color_performance_trends_pops_table}"
    )
except TableAlreadyExistsError:
    print(f"Table '{color_performance_trends_pops_tbl_id}' already exists")
