# Setup Iceberg Catalog using Apache Polaris

The Polaris server does not yet have any catalogs. Run the following script to set up your first catalog, principal, principal role, catalog role, and grants.

By the end of this chapter you would have:

- Created s3 bucket
- Created Catalog named `balloon-game`
- Created Principal `super_user` with Principal Role `admin`
- Created Catalog Role `sudo`, assign the role to Principal Role `admin`
- Granted the Catalog Role `sudo` to manage catalog via `CATALOG_MANAGE_CONTENT` role. This will make the principals with role `admin` able to manage the catalog.
- Created Iceberg database named `balloon_pops`

!!!NOTE
    All values can be adjusted via the [defaults](../../polaris-forge-setup/defaults/main.yml)

## Create Catalog, Principal, Roles and Grants

Run the following command to create the Catalog:

```shell
ansible-playbook $PROJECT_HOME/polaris-forge-setup/catalog_setup.yml
```

!!!NOTE
    The play will set/unset the following environment variables and run the tasks
    ```shell
        unset AWS_PROFILE # just avoid colliding with existing AWS profiles
        export AWS_ENDPOINT_URL=http://localstack.localstack:4566
        export AWS_ACCESS_KEY_ID=test
        export AWS_SECRET_ACCESS_KEY=test
        export AWS_REGION=us-east-1
    ```

## Verify Setup

Run the `$PROJECT_HOME/notebooks/verify_polaris.ipynb` to make sure you are able to create the namespace, table, and insert some data.

To double-check if we have all our iceberg files created and committed, open <https://app.localstack.cloud/inst/default/resources/s3/balloon-game?prefix=demo_db>. You should see something as shown in the screenshots below:

![Localstack](images/verify_polaris.png).