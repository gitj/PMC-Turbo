# Basic configuration for running with no hardware

#------------------------------------------------------------------------------
# GlobalConfiguration(Configurable) configuration
#------------------------------------------------------------------------------

## General configuraion parameters used throughout the balloon

##
c.GlobalConfiguration.controller_pyro_port = 53001

##

##
c.GlobalConfiguration.pipeline_pyro_port = 53000

#------------------------------------------------------------------------------
# BasicPipeline(GlobalConfiguration) configuration
#------------------------------------------------------------------------------

## Initial value for disk write enable flag. If nonzero, start writing to disk
#  immediately
c.BasicPipeline.default_write_enable = 0

##

##
#c.BasicPipeline.num_data_buffers = 16

#------------------------------------------------------------------------------
# AcquireImagesProcess(GlobalConfiguration) configuration
#------------------------------------------------------------------------------

##
#c.AcquireImagesProcess.acquire_counters_name = 'acquire_images'

##
#c.AcquireImagesProcess.camera_housekeeping_subdir = 'camera'

##
#c.AcquireImagesProcess.camera_ip_address = '10.0.0.2'

##
#c.AcquireImagesProcess.initial_camera_configuration = [('PtpMode', 'Slave'), ('ChunkModeActive', '1'), ('AcquisitionFrameCount', '2'), ('AcquisitionMode', 'MultiFrame'), ('StreamFrameRateConstrain', '0'), ('AcquisitionFrameRateAbs', '6.25'), ('TriggerSource', 'FixedRate'), ('ExposureTimeAbs', '100000'), ('EFLensFocusCurrent', '4800')]

##
c.AcquireImagesProcess.use_simulated_camera = True
