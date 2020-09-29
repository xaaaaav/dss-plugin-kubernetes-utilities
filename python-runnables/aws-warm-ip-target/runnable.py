# This file is the actual code for the Python runnable aws-warm-ip-target
from base64 import b64decode as decode
import os
import re
import subprocess

from kubernetes.client.rest import ApiException
import kubernetes.client
import kubernetes.config

from dku_helm.helm_command import Helm

from dataiku.runnables import Runnable
import dataiku

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
        
        self.client = dataiku.api_client()
        
        cluster = self.client.get_cluster(self.config.get('cluster'))
        
        self.kubeconfig = cluster.get_settings().get_raw()['data']['kube_config_path']
        cluster_endpoint = cluster.get_settings().get_raw()['data']['cluster']['Endpoint']
        
        self.cluster_region = re.findall(r'((?:\w+-)+\w+)', cluster_endpoint)[0]
        
        kubernetes.config.load_kube_config(
            config_file = self.kubeconfig
        )
        
    def _install_eks_cni(self):
        """
        Install EKS CNI plugin through helm chart
        """
        cni_env_vars = []
        
        for var in self.config.get("cniEnvVariables"):
            cni_env_vars.append("env.{}={}".format(var["from"], var["to"]))
            
        cni_configs = [
            "originalMatchLabels=true",
            "crd.create=false",
            "image.tag={}".format(self._get_cni_version_tag()),
            "image.region={}".format(self.cluster_region)
        ]
        
        cni_configs.extend(cni_env_vars)
        
        cni_args = ["--set", ",".join(cni_configs)]
        
        if not self.Helm.check_installed("aws-vpc-cni", "kube-system"):
            self.Helm.add_repo("eks", "https://aws.github.io/eks-charts")
            self.Helm.install("aws-vpc-cni", "eks/aws-vpc-cni", "kube-system", cni_args)
        else:
            self.Helm.upgrade("aws-vpc-cni", "eks/aws-vpc-cni", "kube-system", cni_args)
        
        
    def _get_cni_version_tag(self):
        cmd = ["kubectl", "get", "ds", "-n", "kube-system", "aws-node", "-o", "jsonpath='{$.spec.template.spec.containers[:1].image}'"]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()

        if stderr:
            raise Exception("Exception annotating {}: {}".format(kind, stderr))
            
        cni_version = re.findall(r':(.*)\'', stdout)[0]
        
        return cni_version
        
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
        os.environ["KUBECONFIG"] = self.kubeconfig
        
        if self.config.get("adoptExisting"):
            objs = ["daemonSet", "clusterRole", "clusterRoleBinding", "serviceAccount"]

            for kind in objs:
                cmd = ["kubectl", "-n", "kube-system", "annotate", "--overwrite", kind, "aws-node", "meta.helm.sh/release-name=aws-vpc-cni"]
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate()

                if stderr:
                    raise Exception("Exception annotating {}: {}".format(kind, stderr))

                cmd = ["kubectl", "-n", "kube-system", "annotate", "--overwrite", kind, "aws-node", "meta.helm.sh/release-namespace=kube-system"]
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate()

                if stderr:
                    raise Exception("Exception annotating {}: {}".format(kind, stderr))

                cmd = ["kubectl", "-n", "kube-system", "label", "--overwrite", kind, "aws-node", "app.kubernetes.io/managed-by=Helm"]
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate()

                if stderr:
                    raise Exception("Exception labeling {}: {}".format(kind, stderr))
                
        self._install_eks_cni()