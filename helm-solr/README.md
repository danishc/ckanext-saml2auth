
Deploy by running 
```
helm dependency update
helm install solr .
```
The chart doesnot require any PVc or DB to work properly.

See the values.yaml file to configure the endpoint and other settings.