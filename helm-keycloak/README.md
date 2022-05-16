Deploy the helm-db chart before this one,

Deploy by running 
```
helm dependency update
helm install keycloak .
```
The chart will try to connect with postgres DB at 5432.
If successful will create a new DB called keycloak.

see the values.yaml file to configure the endpoint and other settings.