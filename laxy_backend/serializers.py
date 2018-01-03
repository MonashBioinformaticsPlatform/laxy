import pydash
from django.db import transaction
from rest_framework import serializers
from rest_framework.fields import CurrentUserDefault

from . import models


class BaseModelSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        read_only_fields = ('id',)

    def uuid(self, obj):
        if hasattr(obj, 'uuid'):
            return obj.uuid()
        else:
            return obj.id


class FileSerializer(BaseModelSerializer):
    class Meta:
        model = models.File
        fields = '__all__'
        read_only_fields = ('id',)


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
    output_files = FileSerializer(many=True)

    input_fileset_id = serializers.CharField(required=False,
                                             allow_blank=True,
                                             allow_null=True,
                                             max_length=24)
    output_fileset_id = serializers.CharField(required=False,
                                              allow_blank=True,
                                              allow_null=True,
                                              max_length=24)

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

    @transaction.atomic
    def create(self, validated_data):
        """

        :param validated_data:
        :type validated_data:
        :return:
        :rtype:
        """

        input_files_data = validated_data.pop('input_files', [])
        input_fileset_id = validated_data.pop('input_fileset_id', None)
        # Output files can only be updated in a PATCH operation
        # output_files_data = validated_data.pop('output_files', [])
        compute_resource_id = validated_data.pop('compute_resource', None)
        job = models.Job.objects.create(**validated_data)
        job.owner = CurrentUserDefault()

        if compute_resource_id:
            compute = models.ComputeResource.objects.get(id=compute_resource_id)
            job.compute_resource = compute

        # We create new file objects if the input file in the list has
        # details other than the id set. If only the id is set, we assume
        # it's an existing file and use that. If an input_fileset id is provided
        # we ignore anything in input_files and just use the specified FileSet.
        if not input_fileset_id:
            ifileset = models.FileSet.objects.create(
                name=f'Input files for job: {job.id}', job=job, owner=job.owner)
            for f in input_files_data:
                f_id = f.get('id', None)
                if not f_id:
                    input_file = models.File.objects.create(**f)
                    input_file.save()
                else:
                    input_file = models.File.objects.get(id=f_id)

                ifileset.add(input_file)

            ifileset.save()
        else:
            if input_files_data:
                raise serializers.ValidationError("You should only specify an "
                                                  "input_fileset ID or a list "
                                                  "of input_files, not both.")
            ifileset = models.FileSet.objects.get(id=input_fileset_id)

        job.input_files = ifileset

        if not job.output_files:
            job.output_files = models.FileSet.objects.create(
                name=f'Output files for job: {job.id}',
                job=job.id,
                owner=job.owner)
            job.output_files.save()

        job.save()

        return job

    @transaction.atomic
    def update(self, instance, validated_data):
        serializer = JobSerializer(instance,
                                   data=validated_data,
                                   partial=True)

        output_files_data = validated_data.pop('output_files', [])

        # status = validated_data.get('status', instance.status)

        ofiles = []
        for data in output_files_data:
            # We can add files by id if they exist, or create new files
            # from file objects (if id is left unset).
            file_id = data.get('id', None)
            if file_id is None:
                if 'id' in data:
                    del data['id']
                new_file = models.File.objects.create(**data)
                ofiles.append(new_file)
            else:
                # check the file_id actually exists before adding it
                existing_file = models.File.objects.get(id=file_id)
                ofiles.append(file_id)
            # ofile.save()

        instance.output_files.add(ofiles)
        # instance.save()  # instance.output_files.add saves

        return serializer.save()
