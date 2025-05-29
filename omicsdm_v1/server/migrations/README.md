# Single-database configuration for Flask.

Using [Flask-Migrate](https://github.com/miguelgrinberg/flask-migrate) to manage migrations
which is based on [Alembic](https://github.com/sqlalchemy/alembic)

## How to

```bash
FLASK_ENV=development flask db init
FLASK_ENV=development flask db migrate
FLASK_ENV=development flask db upgrade --sql > migrate.sql
```
