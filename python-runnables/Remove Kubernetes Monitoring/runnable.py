# This file is the actual code for the Python runnable Remove Kubernetes Monitoring
from kubernetes.client.rest import ApiException
import kubernetes.client
import kubernetes.config

from dataiku.runnables import Runnable
from dku_helm.helm_command import Helm

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
        
        self.Helm = Helm()
        self.ns = self.config.get("namespace")
        
        kubernetes.config.load_kube_config(
            config_file = self.config.get("kubeConfig")
        )
        
    def get_progress_target(self):
        """
        If the runnable will return some progress info, have this function return a tuple of 
        (target, unit) where unit is one of: SIZE, FILES, RECORDS, NONE
        """
        return None

    def run(self, progress_callback):
        """
        Remove different helm installs and remove the monitoring namespace
        """
        self.Helm.uninstall("prometheus", self.ns)
        self.Helm.uninstall("grafana", self.ns)
        self.Helm.uninstall("elasticsearch", self.ns)
        self.Helm.uninstall("filebeat", self.ns)
        self.Helm.uninstall("kibana", self.ns)
        
        api_instance = kubernetes.client.CoreV1Api()
        try:
            api_response = api_instance.delete_namespace(self.ns, propagation_policy="Foreground")
        except ApiException as e:
            raise Exception("Exception when calling CoreV1Api->delete_namespace: %s\n" % e)
        