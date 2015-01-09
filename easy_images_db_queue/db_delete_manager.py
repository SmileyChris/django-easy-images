"""
This module comes from the desire to use the database cursor to determine the
number of rows that were affected for a DELETE query.

By using this information, a more threadsafe (and multiprocess safe) approach
can be used when consuming items from a queryset.
"""

from django.db import models
from django.db.models import sql, query
from django.db.models.sql.constants import CURSOR


class RowCountDeleteQuery(sql.DeleteQuery):

    def do_query(self, table, where, using):
        self.tables = [table]
        self.where = where
        output = self.get_compiler(using).execute_sql(CURSOR)
        return self.get_row_count(output)

    def get_row_count(self, cursor):
        if isinstance(cursor, int):   # pragma: no cover
            # Future Django versions may have the SQLDeleteCompiler returning
            # the row count natively.
            return cursor
        if not cursor:   # pragma: no cover
            return 0
        try:
            return cursor.rowcount
        finally:
            cursor.close()


class CountDeleteQueryset(query.QuerySet):

    def delete(self):
        """
        Deletes objects found from this queryset in single direct SQL query. No
        signals are sent, and there is no protection for cascades.

        Returns the row count though, so it has that going for it.
        """
        del_query = self._clone()
        # Make sure that the discovery of related objects is performed on the
        # same database as the deletion.
        del_query._for_write = True
        return RowCountDeleteQuery(self.model).do_query(
            table=self.model._meta.db_table, where=del_query.query.where,
            using=del_query.db)
    delete.alters_data = True


class CountDeleteManager(models.Manager):

    def get_queryset(self):
        return CountDeleteQueryset(self.model, using=self._db)

    get_query_set = get_queryset  # Django 1.4 LTS support
