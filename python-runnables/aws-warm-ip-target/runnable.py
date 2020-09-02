# This file is the actual code for the Python runnable aws-warm-ip-target
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
        
        self.Helm = Helm()
        
        kubernetes.config.load_kube_config(
            config_file = self.config.get("kubeConfig")
        )
        
    def _install_eks_cni(self):
        """
        Install EKS CNI plugin through helm chart
        """
        self.Helm.add_repo("eks", "https://aws.github.io/eks-charts")
        
        cni_env_vars = []
        
        for var in self.config.get("cniEnvVariables"):
            cni_env_vars.append("env.{}={}".format(var["from"], var["to"]))
            
        cni_configs = [
            "originalMatchLabels=true",
            "crd.create=false",
            "image.tag={}".format(self.config.get("cniVersionTag"))
        ]
        
        cni_configs.extend(cni_env_vars)
        
        cni_args = ["--set", ",".join(cni_configs)]
        
        self.Helm.install("aws-vpc-cni", "eks/aws-vpc-cni", "kube-system", cni_args)
        
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
        os.environ["KUBECONFIG"] = self.config.get("kubeConfig")
        
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