# This file is the actual code for the Python runnable deploy-spark-history-server
from base64 import b64encode
import os, json

from dataiku.runnables import Runnable
from dku_helm.helm_command import Helm

from kubernetes.client.rest import ApiException
import kubernetes.client
import kubernetes.config

GLOBAL_CONFIGS = [
    "pvc.enablePVC=false",
    "pvc.existingClaimName=nfs-pvc",
    "pvc.eventsDir=\"/\"",
    "nfs.enableExampleNFS=false",
    "nfs.pvName=nfs-pv",
    "nfs.pvcName=nfs-pvc"
]

class S3Manifest:
    def __init__(self, bucket, secret_name):
        self.bucket = bucket
        self.secret_name = secret_name
        self.configs = self.add_s3_configs()
        
    def add_s3_configs(self):
        s3_configs = [
            "s3.enableS3=true",
            "s3.enableIAM=false",
            "s3.secret={}".format(self.secret_name),
            "s3.accessKeyName=aws-access-key",
            "s3.secretKeyName=aws-secret-key",
            "s3.logDirectory=s3a://{}".format(self.bucket)
        ]
        
        return GLOBAL_CONFIGS + s3_configs
    

class GCSManifest:
    def __init__(self, bucket, secret_name, key_name):
        self.bucket = bucket
        self.secret_name = secret_name
        self.key_name = key_name
        self.configs = self.add_gcs_configs()
        
    def add_gcs_configs(self):
        gcs_configs = [
            "gcs.enableGCS=true",
            "gcs.secret={}".format(self.secret_name),
            "gcs.key={}".format(self.key_name),
            "gcs.logDirectory=gs://{}".format(self.bucket)
        ]
        
        return GLOBAL_CONFIGS + gcs_configs
    
    
class WASBManifest:
    def __init__(self, bucket):
        self.bucket = bucket
        self.configs = self.add_wasb_configs()
        
    def add_wasb_configs(self):
        wasb_configs = [
            "wasbs.enableWASBS=true",
            "wasbs.sasKeyMode=false",
            "wasbs.logDirectory=wasbs:///{}".format(self.bucket),
            "image.repository=xthierry/spark-history-server"
        ]
        
        return GLOBAL_CONFIGS + wasb_configs
    
    

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
        
    def get_progress_target(self):
        """
        If the runnable will return some progress info, have this function return a tuple of 
        (target, unit) where unit is one of: SIZE, FILES, RECORDS, NONE
        """
        return None
    
    def _build_namespace(self):
        api_instance = kubernetes.client.CoreV1Api()
        ns_meta = kubernetes.client.V1ObjectMeta(
            name="spark-history-server",
            labels={"name": "spark-history-server"}
        )
        body = kubernetes.client.V1Namespace(metadata=ns_meta)
        
        try:
            api_response = api_instance.create_namespace(body)
        except ApiException as e:
            raise Exception("Exception when calling CoreV1Api->create_namespace: %s\n" % e)
            
    def _install_spark_history_server(self, configs):
        """
        Install grafana dashboards for metric monitoring
        """
        
        spark_history_server_args = ["--set", ",".join(configs)]
        
        self.Helm.install("spark-history-server", "stable/spark-history-server", "spark-history-server", spark_history_server_args)
            
    def _create_ns_secret(self, data, secret_name):
        api_instance = kubernetes.client.CoreV1Api()
        
        secret_meta = kubernetes.client.V1ObjectMeta(
            name=secret_name
        )
        
        secret = kubernetes.client.V1Secret(data=data, metadata=secret_meta)
        
        try:
            api_response = api_instance.create_namespaced_secret("spark-history-server", secret)
        except ApiException as e:
            raise Exception("Exception when calling CoreV1Api->create_namespaced_secret: %s\n" % e)

    def run(self, progress_callback):
        """
        Do stuff here. Can return a string or raise an exception.
        The progress_callback is a function expecting 1 value: current progress
        """
        os.environ["KUBECONFIG"] = self.config.get("kubeConfig")
        self._build_namespace()
        
        if self.config.get("k8sType") == "EKS":
            data = {
                "aws-access-key": b64encode(self.config.get("accessKey")),
                "aws-secret-key": b64encode(self.config.get("secretKey")),
            }
            secret_name = "aws-secrets"
            cloud_manifest = S3Manifest(
                self.config.get("cloudBucket"),
                secret_name
            )
            
        if self.config.get("k8sType") == "GKE":
            data = {
                self.config.get("gcpKeyName"): b64encode(self.config.get("gcpKey"))
            }
            secret_name = "history-secrets"
            cloud_manifest = GCSManifest(
                self.config.get("cloudBucket"),
                secret_name,
                self.config.get("gcpKeyName")
            )
        
        if self.config.get("k8sType") == "AKS":
            data = {
                "azure-storage-account-name": b64encode(self.config.get("storageAccount")),
                "azure-blob-container-name": b64encode(self.config.get("cloudBucket")),
                "azure-storage-account-key": b64encode(self.config.get("storageAccountKey"))
            }
            secret_name = "azure-secrets"
            cloud_manifest = WASBManifest(
                self.config.get("wasbLogDirectory")
            )
        
        self._create_ns_secret(data, secret_name)
        
        self._install_spark_history_server(cloud_manifest.configs)