import os
import subprocess

from dataiku.runnables import ResultTable

class Helm(object):
    
    def __init__(self):
        self.helm = "{}/bin/helm".format(os.path.dirname(os.getenv("DKURUNDIR")))
        
    def add_repo(self, repo, repo_url):
        """
        Add a Helm Charts Repository
        """
        process = subprocess.Popen(
            [self.helm, "repo", "add", repo, repo_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if stderr:
            raise Exception("Exception adding Helm {} charts repository from {}: {}".format(repo, repo_url, stderr))
        
    def install(self, name, repo, namespace, args=[]):
        """
        Install a Helm Chart from a specific Helm Chart Repository and place in namespace
        """
        cmd = [self.helm,"install",name,repo,"--namespace",namespace]
        cmd.extend(args)
        
        print(cmd)
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if stderr:
            raise Exception("Exception installing {} from {}: {}".format(name, repo, stderr))
            
    def search(self, search_term):
        """
        Search the Helm Chart Repositories installed for different Helm charts that can be installed
        """
        rt = ResultTable()
        cmd = [self.helm, "search", "repo"]
        
        if search_term:
            cmd.append(search_term)
            
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if stderr:
            raise Exception("Exception searching repos: {}".format(stderr))
            
        rows = stdout.split("\n")
        result = []
        
        rt.add_column("name", "Name", "STRING")
        rt.add_column("chartVersion", "Chart Version", "STRING")
        rt.add_column("appVersion", "App Version", "STRING")
        rt.add_column("description", "Description", "STRING")

        for row in rows[1:]:
            record = []
            for r in row.split("\t"):
                record.append(r.strip())
            rt.add_record(record)

        return rt
        
            
    def remove_repo(self, repo):
        """
        Remove a Helm Charts Repository
        """
        process = subprocess.Popen(
            [self.helm, "repo", "remove", repo],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if stderr:
            raise Exception("Exception adding Helm {} charts repository from {}: {}".format(repo, repo_url, stderr))
            
    def uninstall(self, name, namespace):
        """
        Uninstall a Helm Chart from a namespace
        """
        cmd = [self.helm, "uninstall", "-n", namespace, name]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if stderr:
            raise Exception("Exception uninstalling {}: {}".format(name, stderr))
            
    def update(self):
        """
        Update Helm Chart Repositories
        """
        process = subprocess.Popen(
            [self.helm,"repo","update"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if stderr:
            raise Exception("Exception updating helm repo: {}".format(stderr))
    