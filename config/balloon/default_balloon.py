import os

# noinspection PyUnresolvedReferences
c = get_config()

c.GlobalConfiguration.data_directories = ['/data1', '/data2', '/data3', '/data4']

c.BasicPipeline.num_data_buffers = 16

housekeeping_dir = '/home/pmc/logs/housekeeping'

c.PipelineApp.housekeeping_dir = housekeeping_dir
c.PipelineApp.counters_dir = os.path.join(housekeeping_dir,'counters')