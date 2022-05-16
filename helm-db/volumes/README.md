pv and pvc used with minikube for local testing

From the directory run following to create volumes
```
kubectl apply -f ./pv-psql.yaml
kubectl apply -f ./pvc-psql.yaml
```

to delete:
```
kubectl delete pvc --all
kubectl delete pv --all
```

