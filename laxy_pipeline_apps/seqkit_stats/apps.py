from laxy.default_settings import JOB_TEMPLATE_PATHS
from django.apps import AppConfig

# This should be the path to the job skeleton templates, relative to
# the app root. In special cases this can also be configured as an
# absolute path (starting with /) if required.
LAXY_JOB_TEMPLATES = "templates/"

# This identifies the app as a pluggable Laxy pipeline definition.
# It needs to match the Pipeline.pipeline_name in the database,
# and also the templates/job_scripts/{pipeline_name} path
LAXY_PIPELINE_NAME = "seqkit_stats"


class SeqkitStatsLaxyPipelineAppConfig(AppConfig):
    name = "laxy_pipeline_apps.seqkit_stats"
