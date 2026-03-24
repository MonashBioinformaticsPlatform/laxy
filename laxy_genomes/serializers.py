from rest_framework import serializers


class ReferenceGenomeFileSerializer(serializers.Serializer):
    location = serializers.CharField()
    name = serializers.CharField(required=False)
    checksum = serializers.CharField(required=False, allow_null=True)
    type_tags = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )


class ReferenceGenomeSerializer(serializers.Serializer):
    id = serializers.CharField()
    organism = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    source = serializers.CharField(required=False, allow_null=True)
    recommended = serializers.BooleanField(required=False, default=False)
    identifiers = serializers.DictField(required=False, allow_null=True)
    checksums = serializers.DictField(required=False, allow_null=True)
    files = ReferenceGenomeFileSerializer(many=True, required=False, default=list)
    tags = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
