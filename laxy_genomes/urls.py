from django.urls import re_path

from laxy_genomes.views import ReferenceGenomesView

urlpatterns = [
    re_path(
        r"^$",
        ReferenceGenomesView.as_view(),
        name="genomes",
    ),
]
