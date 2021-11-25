# ----------------------------------------------------------------------------------------------------------------------
# Simple script for executing one run of a simulation
#
# It will do the following:
# - instantiate the environment
# - the environment will configure itself via the environment variables, config file, or commandline
# - initialize the environment
# - run the environment
# - commit changes to a preferred data store
#
# To get a help with control via the commandline, pass the -h parameter to the runner.
# ----------------------------------------------------------------------------------------------------------------------

from cyst.api.environment.environment import Environment


e = Environment.create()
e.control.init()
e.control.run()
e.control.commit()