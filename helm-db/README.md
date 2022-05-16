## deploy postgresql database on local host or remote server,

- Postgresql 14.2
- Use an already existing PVC.
- Create a db-init.py configmap script to initialize a bd with give name and user.
  - in case if a CKAN_DB variable is also passed to script it will also enable postGIS to be used with ckanext-spatial plugin.
  - see the example how to use the script in helm-ckan or helm-keycloak repositories.

Deploy by running 
```
helm dependency update
helm install db .
```