# This file is the actual code for the Python runnable Kubernetes Monitoring
from base64 import b64decode as decode
import os
import subprocess

from kubernetes.client.rest import ApiException
import kubernetes.client
import kubernetes.config

from dku_helm.helm_command import Helm

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
        self.helm = "{}/bin/helm".format(os.path.dirname(os.getenv("DKURUNDIR")))
        self.ns = self.config.get("namespace")
        self.private = self.config.get("privateNetwork")
        
        self.Helm = Helm()
        
        kubernetes.config.load_kube_config(
            config_file = self.config.get("kubeConfig")
        )
        
    def _build_namespace(self):
        api_instance = kubernetes.client.CoreV1Api()
        ns_meta = kubernetes.client.V1ObjectMeta(
            name=self.ns,
            labels={"name": self.ns}
        )
        body = kubernetes.client.V1Namespace(metadata=ns_meta)
        
        try:
            api_response = api_instance.create_namespace(body)
        except ApiException as e:
            raise Exception("Exception when calling CoreV1Api->create_namespace: %s\n" % e)
            
    def _build_prometheus_config_map(self):
        """
        Deploy config map for prometheus for connecting to grafana
        """
        ds_yml = [
            "apiVersion: 1\n",
            "datasources:\n",
            "- name: Prometheus\n",
            "  type: prometheus\n",
            "  access: proxy\n",
            "  orgId: 1\n",
            "  url: http://prometheus-server.{}.svc.cluster.local".format(self.ns)
        ]
        api_instance = kubernetes.client.CoreV1Api()
        cm_meta = kubernetes.client.V1ObjectMeta(
            name="prometheus-grafana-datasource",
            labels={"grafana_datasource": "1"},
            namespace=self.ns
        )
        body = kubernetes.client.V1ConfigMap(metadata=cm_meta, data={"datasources.yaml": ''.join(ds_yml)})
        
        try:
            api_response = api_instance.create_namespaced_config_map(self.ns, body)
        except ApiException as e:
            raise Exception("Exception when calling CoreV1Api->create_namespaced_config_map: %s\n" % e)
            
    def _get_grafana_hosts(self):
        """
        Return hosts that are exposing grafana
        """
        api_instance = kubernetes.client.CoreV1Api()
        api_response = api_instance.list_node()
        
        hosts = []
        for item in api_response.items:
            for a in item.status.addresses:
                if self.private:
                    if a.type == "InternalIP":
                        hosts.append("http://" + a.address + ":30000")
                else:
                    if a.type == "ExternalIP":
                        hosts.append("http://" + a.address + ":30000")
        
        return hosts
    
    def _get_kibana_hosts(self):
        """
        Return hosts that are exposing kibana
        """
        api_instance = kubernetes.client.CoreV1Api()
        api_response = api_instance.list_node()
        
        hosts = []
        for item in api_response.items:
            for a in item.status.addresses:
                if self.private:
                    if a.type == "InternalIP":
                        hosts.append("http://" + a.address + ":30001")
                else:
                    if a.type == "ExternalIP":
                        hosts.append("http://" + a.address + ":30001")
        
        return hosts
            
    def _get_grafana_creds(self):
        """
        Pull kubernetes secret for grafana and return unencrypted username and password
        """
        api_instance = kubernetes.client.CoreV1Api()
        try:
            api_response = api_instance.read_namespaced_secret("grafana", self.ns)
            user = decode(api_response.data["admin-user"])
            pw = decode(api_response.data["admin-password"])
            return user, pw
        except ApiException as e:
            print("Exception when calling CoreV1Api->read_namespaced_secret: %s\n" % e)
        
            
    def _install_prometheus(self):
        """
        Install prometheus to feed grafana dashboards
        """
        self.Helm.install("prometheus", "stable/prometheus", self.ns)
            
    def _install_elk(self):
        """
        Install the ELK Stack for log monitoring
        """
        self.Helm.install("elasticsearch", "elastic/elasticsearch", self.ns)
        self.Helm.install("filebeat", "elastic/filebeat", self.ns)
        
        kibana_args = ["--set", "service.type=NodePort,service.nodePort=30001,service.targetPort=5601"]
        self.Helm.install("kibana", "elastic/kibana", self.ns, kibana_args)
            
    def _install_grafana(self):
        """
        Install grafana dashboards for metric monitoring
        """
        grafana_configs = [
            "sidecar.datasources.enabled=true",
            "sidecar.datasources.label=grafana_datasource",
            "service.type=NodePort",
            "service.nodePort=30000",
            "sidecar.dashboards.enabled=true",
            "sidecar.dashboards.label=grafana_dashboard"
        ]
        
        grafana_args = ["--set", ",".join(grafana_configs)]
        
        self.Helm.install("grafana", "stable/grafana", self.ns, grafana_args)
            
    def _update_helm_repo(self):
        """
        Update the helm repo for any package updates
        """
        self.Helm.update()
        
    def get_progress_target(self):
        """
        If the runnable will return some progress info, have this function return a tuple of 
        (target, unit) where unit is one of: SIZE, FILES, RECORDS, NONE
        """
        return None

    def run(self, progress_callback):
        """
        Installs and configures the required Helm charts for monitoring the cluster.
        """
        os.environ["KUBECONFIG"] = self.config.get("kubeConfig")
        self._build_namespace()
        self._update_helm_repo()
        self._install_prometheus()
        self._build_prometheus_config_map()
        self._install_grafana()
        self._install_elk()
        ghosts = self._get_grafana_hosts()
        khosts = self._get_kibana_hosts()
        user, pw = self._get_grafana_creds()
        
        del os.environ["KUBECONFIG"]
        
        return "<h5>HOSTS: <a href=\"{}\" target=\"_blank\">Grafana</a>, <a href=\"{}\" target=\"_blank\">Kibana</a></h5>\n<h5>GRAFANA USER: {}</h5>\n<h5>GRAFANA PASSWORD: {}</h5>".format(ghosts[0], khosts[0], user, pw)