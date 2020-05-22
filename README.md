# dss-plugin-kubernetes-utilities
A suite of kubernetes utilities as a Dataiku DSS Plugin.

## Capabilities
* Install/Uninstall Helm
* Install/Uninstall Helm Charts
* Add/Remove Helm Chart Repositories
* Search Helm Chart Repositories
* Install/Uninstall Kubernetes Monitoring

## Helm
Helm is an application package manager running atop Kubernetes. It allows describing the application structure through convenient helm-charts and managing it with simple commands.

## Kubernetes Monitoring
The monitoring stack that is deployed with this plugin includes the following:
* Prometheus - a time-series mertrics database
* Grafana - dashboarding tool for visualizing real-time data, like metrics
* ELK Stack - Elasticsearch, Logstash, and Kibana used for collecting, indexing, and visualizing container logs
