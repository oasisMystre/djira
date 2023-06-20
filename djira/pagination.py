from collections import OrderedDict

from django.db.models.query import QuerySet
from django.core.paginator import Paginator, Page

from rest_framework.pagination import _positive_int


from .scope import Scope
from .settings import jira_settings


class BasePagination:
    page_size = jira_settings.PAGE_SIZE

    def paginate_queryset(self, querset: QuerySet, scope: Scope) -> Page:
        raise NotImplementedError(
            "override `.paginate_queryset method` in %s class" % self.__class__.__name__
        )

    def paginate_response(self, data: list):
        raise NotImplementedError(
            "override `.paginate_response` in %s class" % self.__class__.__name__
        )


class PagePagination:
    def paginate_queryset(self, queryset: QuerySet, scope: Scope):
        page = _positive_int(scope.query.get("page", 1))
        page_size = _positive_int(scope.query.get("page_size", 8))

        paginator = Paginator(queryset, page_size)

        self.page = paginator.get_page(page)

        return list(self.page)

    def paginate_response(self, data: list):
        return OrderedDict(
            {
                "count": self.page.count(data),
                "next_page": self.page.next_page_number()
                if self.page.has_next()
                else None,
                "previous_page": self.page.previous_page_number()
                if self.page.has_previous()
                else None,
                "results": data,
            }
        )
