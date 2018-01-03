
def generate_cluster_stack_name(job):
    """
    Given a job, generate a name for an associated compute cluster resource.

    Since this becomes an AWS (or OpenStack?) Stack name via CloudFormation
    it can only contain alphanumeric characters (upper and lower) and hyphens
    and cannot be longer than 128 characters.

    :param job: A Job instance (with ComputeResource assigned)
    :type job: Job
    :return: A cluster ID to use as the stack name.
    :rtype: str
    """
    return 'cluster-%s----%s' % (job.compute_resource.id, job.id)
