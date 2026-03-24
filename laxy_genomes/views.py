import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from laxy_genomes.data.genomes import reference_genomes_for_api
from laxy_genomes.serializers import ReferenceGenomeSerializer

logger = logging.getLogger(__name__)


class ReferenceGenomesView(APIView):
    renderer_classes = (JSONRenderer,)
    permission_classes = (AllowAny,)
    api_docs_visible_to = "public"

    @extend_schema(
        responses=ReferenceGenomeSerializer(many=True),
        description="Returns a list of available reference genomes.",
    )
    def get(self, request, version=None):
        """
        Returns a list of available reference genomes.
        The genomes are sourced from REFERENCE_GENOMES.
        """
        genomes = reference_genomes_for_api()
        serializer = ReferenceGenomeSerializer(genomes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
