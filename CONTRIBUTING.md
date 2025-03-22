# Developer guide

## Getting started
Ensure you have the development environment setup by running the following commands:
```bash
conda env create -n extralit -f environment_dev.yml
conda activate extralit
```

## Updating the database schema
Modify the `[database model code](src/argilla/server/models/database.py)` to define the database's declarative schema.

Then, to apply the changes to the database run the following command:

```bash
# From your development machine, Set the 4 env variables below, and ensure that ARGILLA_ELASTICSEARCH_HOST and POSTGRES_HOST are reachable
export ARGILLA_ELASTICSEARCH=https://elastic:$ELASTIC_PASSWORD@$ARGILLA_ELASTICSEARCH_HOST
export ARGILLA_DATABASE_URL=postgresql://postgres:$POSTGRES_PASSWORD@$POSTGRES_HOST/postgres

# Run the database migration script
python -m argilla server database migrate

# Run the upgrade
cd src/argilla
alembic revision --autogenerate -m "<Title of the changes>"
alembic upgrade head
```


## Want to work on your own?

For more seasoned contributors, we recommend taking a look at the [contributor section](https://docs.extralit.ai/latest/community/contributor/) in our docs.

