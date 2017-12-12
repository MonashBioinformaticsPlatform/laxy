from rest_framework import serializers

from . import models


class BaseModelSerializer(serializers.ModelSerializer):

    def uuid(self, obj):
        if hasattr(obj, 'uuid'):
            return obj.uuid()
        else:
            return obj.id


class FileSerializer(BaseModelSerializer):
    class Meta:
        model = models.File
        fields = '__all__'
        read_only_fields = ('id', 'job')


class ComputeResourceSerializer(BaseModelSerializer):
    gateway_server = serializers.CharField(required=False,
                                           max_length=255)

    class Meta:
        model = models.ComputeResource
        fields = '__all__'
        # not actually required for id since editable=False on model
        read_only_fields = ('id',)
        depth = 1


class JobSerializer(BaseModelSerializer):
    input_files = FileSerializer(many=True)
    params = serializers.JSONField()
    compute_resource = serializers.CharField(required=False,
                                             allow_blank=True,
                                             allow_null=True,
                                             max_length=24)

    class Meta:
        model = models.Job
        fields = '__all__'
        # not actually required for id since editable=False on model
        read_only_fields = ('id',)
        depth = 1

    def create(self, validated_data):
        # TODO: input_file_data might be better as a FileSet
        input_file_data = validated_data.pop('input_files')
        compute_resource_id = validated_data.pop('compute_resource', None)
        job = models.Job.objects.create(**validated_data)

        if compute_resource_id:
            compute = models.ComputeResource.objects.get(id=compute_resource_id)
            job.compute_resource = compute

        job.save()
        for infiledata in input_file_data:
            sfile = models.File.objects.create(job=job, **infiledata)
            sfile.save()

        return job

    # def update(self, instance, validated_data):
    #     serializer = JobSerializer(instance,
    #                                data=validated_data,
    #                                partial=True)
    #     # status = validated_data.get('status', instance.status)
    #     # instance.save()
    #     return serializer.save()



