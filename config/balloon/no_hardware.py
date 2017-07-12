# Basic configuration for running with no hardware
import os
from pmc_turbo import root_dir
#------------------------------------------------------------------------------
# GlobalConfiguration(Configurable) configuration
#------------------------------------------------------------------------------

## General configuraion parameters used throughout the balloon

##
c.GlobalConfiguration.controller_pyro_port = 53001

##

##
c.GlobalConfiguration.pipeline_pyro_port = 53000

## List of tuples - hirate downlink name, Enum(("openport", "highrate", "los"))
#  hirate downlink address,
#  hirate downlink downlink speed in bytes per second. 0 means link is disabled.
#  e.g. [("openport", ("192.168.1.70", 4501), 10000), ...]
c.Communicator.hirate_link_parameters = [('highrate', ('localhost', 50002), 700000),
                                         ('openport', ('localhost', 45001), 1000000),
                                         ('los', ('localhost', 50004), 100000)]

c.Controller.hot_pixel_file_dictionary = {4:'hot_pixels_02-2636D-07229_000f3102fb57.npy',
                                          }
JSON_FILENAMES = [
    'camera_items.json',
    'charge_controller_register_items.json',
    'charge_controller_eeprom_items.json',
    'counter_items.json',
    'collectd_items.json',
    'labjack_items.json'
]

c.Communicator.json_paths = [os.path.join(os.path.split(root_dir)[0], 'status_item_params', json_fn) for json_fn in JSON_FILENAMES]


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


