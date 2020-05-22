# This file is the actual code for the Python runnable Remove Helm
import os.path
import subprocess

from dataiku.runnables import Runnable

class MyRunnable(Runnable):
    """The base interface for a Python runnable"""

    def __init__(self, project_key, config, plugin_config):
        """
        :param project_key: the project in which the runnable executes
        :param config: the dict of the configuration of the object
        :param plugin_config: contains the plugin settings
        """
        self.project_key = project_key
        self.config = config
        self.plugin_config = plugin_config
        
        self.tmp_dir = "{}/tmp/helm".format(os.path.dirname(os.getenv("DKURUNDIR")))
        self.helm = "{}/bin/helm".format(os.path.dirname(os.getenv("DKURUNDIR")))
        
    def get_progress_target(self):
        """
        If the runnable will return some progress info, have this function return a tuple of 
        (target, unit) where unit is one of: SIZE, FILES, RECORDS, NONE
        """
        return None

    def run(self, progress_callback):
        """
        Do stuff here. Can return a string or raise an exception.
        The progress_callback is a function expecting 1 value: current progress
        """
        
        if os.path.exists(self.tmp_dir):
            process = subprocess.Popen(
                ["rm","-rf",self.tmp_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if stderr:
                raise Exception("Exception removing helm installer: {}".format(stderr))
                
        if os.path.exists(self.helm):
            process = subprocess.Popen(
                ["rm","-rf",self.helm],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if stderr:
                raise Exception("Exception removing helm installer: {}".format(stderr))
        