import os
import argparse


# helper class from stack overflow to add env to argparse
# it allows to use env variables as default values for arguments
class EnvDefault(argparse.Action):
    def envvar(self, envvar):
        return os.environ.get(envvar)

    def __init__(self, envvar, required=True, default=None, **kwargs):
        if envvar in os.environ:
            default = os.environ[envvar]
        if required and default:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required, **kwargs)

    def __call__(self, parse, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)