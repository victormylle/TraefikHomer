# Traefik Homer for Kubernetes

Traefik Homer is an application built on top of Homer that automatically displays all the IngressRoutes in the Kubernetes cluster.
---
## Prerequisites

Before getting started, ensure you have the following prerequisites:

- Kubernetes cluster up and running
- `kubectl` command-line tool installed and configured
- Docker registry for hosting your Traefik Homer Docker image
- Basic understanding of Traefik and Kubernetes concepts
---
## Installation

I made this to use it myself. Therefor, I pushed the image to my private docker registry. This means if you want to deploy it yourself, you'll need to build it yourself and deploy it to your own private docker registry. (Maybe I'll push it to Dockerhub in the future)

### Building the image
To build and push the image to a docker registry. First make sure you're logged in for the private docker registry (docker login). Because my docker registry is only locally accessible, I deployed it insecurely therefor the following must be done to push the image to the registry.


**File: buildkit.toml**
```toml
[registry."<REGISTRY-DOMAIN>"]
insecure = true
```

Next, we can build and push the image by executing the following command. Make sure you build for the platform you want.

```
docker buildx create --use --config buildkit.toml
docker buildx build --push --platform linux/arm64/v8,linux/amd64 \
                    --tag <REGISTRY-DOMAIN>/traefikhomer:latest .
```

### Deploying on cluster
I haven't had the time to create a Helm chart for this. I deployed it by using the following config.
The Role and ClusterRole are needed to fetch all IngressRoutes in the cluster. These are binded to the ServiceAccount that will be attached to the Pod.

```
apiVersion: v1
kind: ServiceAccount
metadata:
  name: traefik-homer-service-account
  namespace: traefik-homer
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: ingressroute-reader-clusterrole
rules:
  - apiGroups: ["traefik.containo.us"]
    resources: ["ingressroutes"]
    verbs: ["get", "watch", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-ingressroutes-clusterrolebinding
subjects:
  - kind: ServiceAccount
    name: traefik-homer-service-account
    namespace: traefik-homer
roleRef:
  kind: ClusterRole
  name: ingressroute-reader-clusterrole
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: traefik-homer
  name: ingressroute-reader
rules:
- apiGroups: ["traefik.containo.us"]
  resources: ["ingressroutes"]
  verbs: ["get", "watch", "list", "create"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-ingressroutes
  namespace: traefik-homer
subjects:
- kind: ServiceAccount
  name: traefik-homer-service-account
  namespace: traefik-homer
roleRef:
  kind: Role
  # namespace: traefik-homer
  name: ingressroute-reader
  apiGroup: rbac.authorization.k8s.io
```

We can also use a ConfigMap that specifies custom pages and services. This is just the Homer configuration (https://github.com/bastienwirtz/homer/blob/main/docs/configuration.md). The IngressRoutes will be dynamically added to these files. An example can be seen below.
```
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-map
  namespace: traefik-homer
data:
  config.yml: |
    title: "Optimize"
    subtitle: "Homer"
    logo: "assets/logo.png"
    links:
      - name: "Home"
        icon: "fas fa-home"
        url: "#"
      - name: "Test"
        icon: "fas fa-home"
        url: "#file2"
    services: []
  file2.yml: |
    services: []
```

The deployment and service is then created which has the ConfigMap and ServiceAccount attached to it.

```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: traefik-homer-deployment
  namespace: traefik-homer
spec:
  selector:
    matchLabels:
      app: traefik-homer
  replicas: 1
  template:
    metadata:
      labels:
        app: traefik-homer
    spec:
      serviceAccountName: traefik-homer-service-account
      containers:
      - name: traefik-homer
        image: <REGISTRY-DOMAIN>/traefikhomer:latest
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: config-volume
          mountPath: /files/config.yml
          subPath: config.yml
        env:
        - name: CONFIGDIR_PATH
          value: "/files"
      imagePullSecrets:
        - name: regcred
      volumes:
      - name: config-volume
        configMap:
          name: config-map
---
apiVersion: v1
kind: Service
metadata:
  name: traefik-homer-service
  namespace: traefik-homer
spec:
  type: ClusterIP
  ports:
  - port: 8080
  selector:
    app: traefik-homer
```

Lastly, we can apply an IngressRoute so the dashboard is externally available.

```
apiVersion: traefik.containo.us/v1alpha1
kind: IngressRoute
metadata:
  name: traefik-homer-ingress
  namespace: traefik-homer
spec:
  entryPoints:
    - web
  routes:
    - match: Host(`services.kube.optimize`)
      kind: Rule
      services:
        - name: traefik-homer-service
          namespace: traefik-homer
          port: 8080
```
---
## Usage
To customize the dashboard, the ConfigMap described in the previous section can be modified. There are also some annotations available for the IngressRoutes.

- homer/name
- homer/page
- homer/group
- homer/logo

These annotations add some customization to the services. As default, the namespace and such are used. Every minute the IngressRoutes are fetched again and the Homer dashboard gets updated.

**Example IngressRoute**
```
apiVersion: traefik.containo.us/v1alpha1
kind: IngressRoute
metadata:
  name: frigate-ingress
  annotations:
    homer/name: "Frigate"
    homer/page: "Smart Home"
    homer/group: "Security"
    homer/logo: "https://docs.frigate.video/img/logo.svg"
spec:
  entryPoints:
    - web
  routes:
    - match: Host(`frigate.kube.optimize`)
      kind: Rule
      services:
        - name: frigate
          namespace: home-assistant
          port: 5000
```