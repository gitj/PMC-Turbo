# Configuration file for application.
# noinspection PyUnresolvedReferences
c = get_config()

#------------------------------------------------------------------------------
# Application(SingletonConfigurable) configuration
#------------------------------------------------------------------------------

## This is an application.

## The date format used by logging formatters for %(asctime)s
#c.Application.log_datefmt = '%Y-%m-%d %H:%M:%S'

## The Logging format template
#c.Application.log_format = '[%(name)s]%(highlevel)s %(message)s'

## Set the log level by value or name.
#c.Application.log_level = 30

#------------------------------------------------------------------------------
# CommandSenderApp(Application) configuration
#------------------------------------------------------------------------------

## This is an application.

## Config file directory
#c.CommandSenderApp.config_dir = '/home/pmc/pmchome/pmc-turbo-devel/config/ground'

## Load this config file
#c.CommandSenderApp.config_file = u'default_ground_config.py'

## Write template config file to this location
#c.CommandSenderApp.write_default_config = u''

#------------------------------------------------------------------------------
# GroundConfiguration(Configurable) configuration
#------------------------------------------------------------------------------

## 
#c.GroundConfiguration.command_history_subdir = 'command_history'

## 
#c.GroundConfiguration.command_index_filename = 'index.csv'

## Serial device connected to GSE uplink. Empty string means don't use serial (GSE) uplink (only openport
c.GroundConfiguration.command_port = ''

## (IP,port) tuple to send OpenPort commands to
c.GroundConfiguration.openport_uplink_address = ('pmc-camera-4', 5001)

## 
#c.GroundConfiguration.root_data_path = '/data/gse_data'

#------------------------------------------------------------------------------
# CommandSender(GroundConfiguration) configuration
#------------------------------------------------------------------------------

## Timeout for serial command port. This sets how much time is allocated for the
#  GSE to acknowledge the command we sent.
#c.CommandSender.command_port_response_timeout = 3.0
