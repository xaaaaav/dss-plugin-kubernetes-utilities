# This file is the actual code for the Python runnable Install Helm
import os
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

        self.data_dir = os.path.dirname(os.getenv("DKURUNDIR"))
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
        
        if not os.path.exists(self.tmp_dir):
            process = subprocess.Popen(
                ["curl", "-fsSL", "-o", self.data_dir+"/tmp/helm/get_helm.sh", "https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3", "--create-dirs"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if stderr:
                raise Exception("Exception downloading helm installer: {}".format(stderr))

            bin_dir = "{}/bin".format(self.data_dir)
            escaped_bin_dir = bin_dir.replace("/", "\/")

            process = subprocess.Popen(
                ["sed","-i","s/\/usr\/local\/bin/{}/g".format(escaped_bin_dir),"{}/tmp/helm/get_helm.sh".format(self.data_dir)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if stderr:
                raise Exception("Exception updating helm installer: {}".format(stderr))

            process = subprocess.Popen(
                ["chmod","+x","{}/tmp/helm/get_helm.sh".format(self.data_dir)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if stderr:
                raise Exception("Exception updating permissions on helm installer: {}".format(stderr))
        
        if not os.path.exists(self.helm):
            process = subprocess.Popen(
                ["bash","{}/tmp/helm/get_helm.sh".format(self.data_dir), "--no-sudo"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if stderr:
                raise Exception("Exception executing helm installer: {}".format(stderr))

            process = subprocess.Popen(
                ["{}/helm".format(bin_dir), "repo", "add", "stable", "https://kubernetes-charts.storage.googleapis.com/"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if stderr:
                raise Exception("Exception adding Helm stable charts repository: {}".format(stderr))

            process = subprocess.Popen(
                ["{}/helm".format(bin_dir), "repo", "add", "elastic", "https://Helm.elastic.co"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if stderr:
                raise Exception("Exception adding Helm elastic charts repository: {}".format(stderr))
