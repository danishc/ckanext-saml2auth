Based on https://github.com/keitaroinc/ckan-helm

## 1. Install on minikube with helm

### 1.1. Requirements to run helm app on minikube

    1: minikube v1.24.0+ with ingress enabled
    2: image: knowhub.disi.unitn.it:4443/datascientia_ckan_platform
    3: pvc for psql (helm-db)
    4: helm to deploy on minikube

### 1.2. Configuration
1. Make sure ingress addons is enabled ```minikube addons enable ingress```
2. Add the minikube ip and baseDomain in ```/etc/hosts``` 
   * example default value
    ```
    192.168.49.2    ds.datascientia.local
    192.168.49.2    livepeople.datascientia.local
    192.168.49.2    livelanguage.datascientia.local
    ```
   * check the ingress for minikube documentation for more detail https://kubernetes.io/docs/tasks/access-application-cluster/ingress-minikube/
    
3. Load the updated images from host machine to minikube
    ```
    $ minikube image load <name-of-image>:<tage-of-image>
   ```

4. Deploy solr app from ./helm-solr:
    ```
    $ helm install solr .
    ```
5. Deploy db app:
   * Volume setup from ./helm-db/volumes
     ```
     $ kubectl apply -f ./pv-psql.yaml
     $ kubectl apply -f ./pvc-psql.yaml
     ```
   * App Deploy from ./helm-db
     ```
     $ helm dependency update 
     $ helm install db .
     ```
6. Deploy keycloak app from ./helm-keycloak:
    
    Make sure to update value.yaml file with ckan image version. 
    ```
    $ helm dependency update
    $ helm install keycloak .
    ```
    #### Setup from keycloak GUI

   1. login to the admin console from Keycloak GUI
      1. create new realm by the name of "myrealm"
         1. from the login tab
            1. turn on user register (be cautious as it will allow anyone to signup using GUI)
            2. turn on remember me
      2. create a new client using `./helm-ckan/keycloak-client/local/conf-saml2-client-sp-metadata.xml` file, it will be called "myclient"
      3. open the client settings
         1. from setting tab:
            1. Turn off Client Signature Required
         2. from keys tab
            2. generate new keys and copy-paste them to new files for private key and cert in `./helm-ckan/keycloak-client/local/*`.
            3. if needed, update the link to the files in the ckan.ini configuration file.
         3. from mappers tab click "Add BuildIn" and select all the default mappings.
      4. from realm setting in general tab
         1. from endpoints field copy the saml 2.0 metadata content to a a file in `./helm-ckan/keycloak-client/local/saml2-idp-metadata.xml`
         2. if needed, update the link to this file to ckan.ini configuration.   

7. Deploy ckan app from ./helm-ckan:

    Make sure to update value.yaml file with ckan image version. 
    ```
    $ helm dependency update
    $ helm install <name-of-app> .
    ```
   Make sure to update values.yaml with new ckan image name and tag.


## 2. Requirements to deploy ckan app on kubernates/rancher server

Do the following changes to the values.yaml files for helm-db, helm-keycloak and helm-ckan with appropriate values and follow the instructions in the 1.2, 

1. Update the pvc name and passwords, here is the list of default values:
    ```
    #DB
    
    #PVCposgresql: &PVCposgresql ckan-postgres-persistent-volume-claim the name of the claim
    PVCposgresql: &PVCposgresql psql
    
    # MasterDBPass -- Variable for password for the master/main database user in PostgreSQL
    MasterDBUserPass: &MasterDBUserPass password
    
    # DBDeploymentName -- Variable for name override for postgres deployment
    DBDeploymentName: &DBDeploymentName postgres
    
    
    #KeyCloak
    
    # Endpoint where keycloak service will be deployed using ingress.
    CKANSite: &CKANsite ds.datascientia.local
    
    # KeyCloakDBPass -- Variable for password for the keycloak user in PostgreSQL
    KeyCloakDBPass: &KeyCloakDBPass password
    
    # -- variable for keycloak admin password
    KeyCloakAdminPass: &KeyCloakAdminPass password
    
    
    
    #CKAN
    
    CKANSysAdminPass: &CKANSysAdminPass password
   
    # CkanDBUserPass -- Variable for password for the CKAN database user
    CkanDBUserPass: &CkanDBUserPass password
   
    # MasterDBUserPass -- Variable for password for the master user in PostgreSQL
    MasterDBUserPass: &MasterDBUserPass password
    
    ParentDomain: &ParentDomain datascientia.local
    CKANSite: &CKANsite ds.datascientia.local
    LiveLanguageSite: &LiveLanguageSite livelanguage.datascientia.local
    LivePeopleSite: &LivePeopleSite livepeople.datascientia.local
    CKANSiteFull: &CKANsiteFull "https://ds.datascientia.local/"
    
    ```


2. Uncomment/update the resource and affinity settings in each values.yaml file.
3. Setup the regcred secret to pull the ckan image to rancher: https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/#create-a-secret-by-providing-credentials-on-the-command-line