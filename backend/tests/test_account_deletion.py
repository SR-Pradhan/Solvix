from app.api.users import OWNED_BY_USER
from app.db.database import Base


def tables_with_a_user_id() -> set[str]:
    """Every mapped table carrying a user_id, read from the models themselves."""
    return {
        table.name
        for table in Base.metadata.tables.values()
        if "user_id" in table.columns
    }


def test_deleting_an_account_covers_every_table_that_belongs_to_one():
    # The guard for an explicit delete list: add a table with a user_id and
    # forget to list it, and this fails rather than leaving rows behind that
    # reference an account nobody can log into.
    listed = {model.__tablename__ for model in OWNED_BY_USER}
    assert tables_with_a_user_id() == listed


def test_the_list_holds_no_duplicates():
    listed = [model.__tablename__ for model in OWNED_BY_USER]
    assert len(listed) == len(set(listed))


def test_the_users_table_is_not_in_the_list():
    # It is deleted separately, after its children; listing it here would try
    # to remove the row twice.
    assert "users" not in {model.__tablename__ for model in OWNED_BY_USER}
