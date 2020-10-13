from rest_framework import filters


class IsOwnerFilter(filters.BaseFilterBackend):
    """
    Filter that only allows users to see their own objects.
    """

    def filter_queryset(self, request, queryset, view):
        return queryset.filter(owner=request.user)


class IsPublicFilter(filters.BaseFilterBackend):
    """
    Filter that allows users to see objects with a public flag.
    """

    def filter_queryset(self, request, queryset, view):
        return queryset.filter(public=True)
