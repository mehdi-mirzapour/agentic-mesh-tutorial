# Kubernetes Deployment Strategy

## Design Philosophy: One Container Per Role

In this architecture, **no agent communicates directly with another**. All coordination happens through Redis Streams. This makes containerisation natural — each agent only needs to know its Redis address, its input stream, and its output stream.

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌───────────────┐
│  Producer   │────▶│ Coordinator  │────▶│ Grammar Agent(s) │────▶│               │
│   (Job)     │     │ (Deployment) │     │  (Deployment)    │     │  Aggregator   │
│             │     │              │     ├──────────────────┤     │  (Deployment) │
│             │     │              │     │ Clarity Agent(s) │────▶│               │
│             │     │              │     ├──────────────────┤     │               │
│             │     │              │     │ Tone Agent(s)    │────▶│               │
│             │     │              │     ├──────────────────┤     │               │
│             │     │              │     │ Structure Agent  │────▶│               │
└─────────────┘     └──────────────┘     └──────────────────┘     └───────────────┘
                           │                       │
                           └─────────── Redis ─────┘
                                    (StatefulSet)
```

---

## Container Roles

| Component | K8s Kind | Replicas | Reason |
|---|---|---|---|
| **Producer** | `Job` | 1 (per doc) | Runs once, sends chunks, exits |
| **Coordinator** | `Deployment` | 1 | Lightweight fan-out, no scaling needed |
| **Grammar Agent** | `Deployment` | 1–N | Scale based on queue depth |
| **Clarity Agent** | `Deployment` | 1–N | Scale based on queue depth |
| **Tone Agent** | `Deployment` | 1–N | Scale based on queue depth |
| **Structure Agent** | `Deployment` | 1–N | Scale based on queue depth |
| **Aggregator** | `Deployment` | 1 | Collects all results |
| **Redis** | `StatefulSet` | 1 | Persistent message store |

---

## Prerequisites

- A Kubernetes cluster (e.g., AKS, GKE, EKS, or local Minikube)
- `kubectl` configured to your cluster
- Docker image built and pushed to a registry

```bash
# Build and push the image
docker build -t your-registry/agentic-mesh:latest .
docker push your-registry/agentic-mesh:latest
```

---

## Namespace

Keep all services isolated in their own namespace:

```bash
kubectl create namespace agentic-mesh
```

---

## Manifests

### 1. Redis (StatefulSet + Service)

Redis requires a `StatefulSet` (not a `Deployment`) to preserve its data volume across pod restarts.

```yaml
# k8s/redis.yaml
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: agentic-mesh
spec:
  selector:
    app: redis
  ports:
    - port: 6379
      targetPort: 6379
  clusterIP: None   # Headless service for StatefulSet DNS
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: agentic-mesh
spec:
  serviceName: redis
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: redis-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 5Gi
```

---

### 2. Shared ConfigMap (Environment)

All agents share the same Redis connection details via a `ConfigMap`:

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mesh-config
  namespace: agentic-mesh
data:
  REDIS_HOST: "redis.agentic-mesh.svc.cluster.local"
  REDIS_PORT: "6379"
  REDIS_DB: "0"
```

---

### 3. Coordinator (Deployment)

```yaml
# k8s/coordinator.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: coordinator
  namespace: agentic-mesh
spec:
  replicas: 1
  selector:
    matchLabels:
      app: coordinator
  template:
    metadata:
      labels:
        app: coordinator
    spec:
      containers:
      - name: coordinator
        image: your-registry/agentic-mesh:latest
        args: ["coordinator"]
        envFrom:
        - configMapRef:
            name: mesh-config
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "250m"
            memory: "256Mi"
```

---

### 4. Specialist Agents (Deployments, one per type)

Each specialist is a separate `Deployment`. They use the same image but different `args`.

```yaml
# k8s/specialists.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grammar-agent
  namespace: agentic-mesh
spec:
  replicas: 2    # Run 2 grammar checkers in parallel
  selector:
    matchLabels:
      app: grammar-agent
  template:
    metadata:
      labels:
        app: grammar-agent
    spec:
      containers:
      - name: grammar-agent
        image: your-registry/agentic-mesh:latest
        args: ["specialist", "--type", "grammar"]
        envFrom:
        - configMapRef:
            name: mesh-config
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: clarity-agent
  namespace: agentic-mesh
spec:
  replicas: 1
  selector:
    matchLabels:
      app: clarity-agent
  template:
    metadata:
      labels:
        app: clarity-agent
    spec:
      containers:
      - name: clarity-agent
        image: your-registry/agentic-mesh:latest
        args: ["specialist", "--type", "clarity"]
        envFrom:
        - configMapRef:
            name: mesh-config
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tone-agent
  namespace: agentic-mesh
spec:
  replicas: 1
  selector:
    matchLabels:
      app: tone-agent
  template:
    metadata:
      labels:
        app: tone-agent
    spec:
      containers:
      - name: tone-agent
        image: your-registry/agentic-mesh:latest
        args: ["specialist", "--type", "tone"]
        envFrom:
        - configMapRef:
            name: mesh-config
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: structure-agent
  namespace: agentic-mesh
spec:
  replicas: 1
  selector:
    matchLabels:
      app: structure-agent
  template:
    metadata:
      labels:
        app: structure-agent
    spec:
      containers:
      - name: structure-agent
        image: your-registry/agentic-mesh:latest
        args: ["specialist", "--type", "structure"]
        envFrom:
        - configMapRef:
            name: mesh-config
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
```

---

### 5. Aggregator (Deployment)

```yaml
# k8s/aggregator.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aggregator
  namespace: agentic-mesh
spec:
  replicas: 1
  selector:
    matchLabels:
      app: aggregator
  template:
    metadata:
      labels:
        app: aggregator
    spec:
      containers:
      - name: aggregator
        image: your-registry/agentic-mesh:latest
        args: ["aggregator"]
        envFrom:
        - configMapRef:
            name: mesh-config
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "250m"
            memory: "256Mi"
```

---

### 6. Producer (Job)

The producer is not a long-running service — it's triggered on demand. In Kubernetes, use a `Job`:

```yaml
# k8s/producer-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: producer-run-001
  namespace: agentic-mesh
spec:
  ttlSecondsAfterFinished: 300   # Clean up 5 minutes after completion
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: producer
        image: your-registry/agentic-mesh:latest
        args: ["produce", "--doc_id", "doc-001", "--paragraphs", "5"]
        envFrom:
        - configMapRef:
            name: mesh-config
```

Trigger it manually:
```bash
kubectl apply -f k8s/producer-job.yaml -n agentic-mesh
```

---

## Deployment Order

Apply manifests in this order to respect dependencies:

```bash
# 1. Namespace
kubectl create namespace agentic-mesh

# 2. Shared config
kubectl apply -f k8s/configmap.yaml

# 3. Redis (wait until pod is Running before continuing)
kubectl apply -f k8s/redis.yaml
kubectl wait --for=condition=ready pod -l app=redis -n agentic-mesh --timeout=60s

# 4. All agents (order doesn't matter — they block on Redis)
kubectl apply -f k8s/coordinator.yaml
kubectl apply -f k8s/specialists.yaml
kubectl apply -f k8s/aggregator.yaml

# 5. Trigger a test run
kubectl apply -f k8s/producer-job.yaml
```

---

## Scaling a Specific Specialist

If the `grammar` stream is backing up (check with `XLEN doc.review.grammar`), scale only that agent:

```bash
kubectl scale deployment grammar-agent --replicas=4 -n agentic-mesh
```

Redis automatically distributes messages within the `grammar-group` consumer group across all 4 replicas. **No code changes required.**

---

## Monitoring Stream Health

Watch stream queue depths from within the cluster:

```bash
# Port-forward Redis to local machine
kubectl port-forward svc/redis 6379:6379 -n agentic-mesh

# Then inspect streams
redis-cli XLEN doc.review.grammar         # Pending grammar tasks
redis-cli XLEN doc.suggestions.grammar    # Suggestions produced
redis-cli XPENDING doc.review.grammar grammar-group  # Unacknowledged messages
```

---

## Why This Works

The key insight is that **Redis Consumer Groups provide built-in load balancing**. When you add more replicas of `grammar-agent`, they all register under the same `grammar-group`. Redis handles distribution automatically — you scale by adding containers, not by changing any code.

```
doc.review.grammar stream
        │
        ├──▶ grammar-1 (container 1)  ← message A, C, E
        ├──▶ grammar-2 (container 2)  ← message B, D, F
        └──▶ grammar-3 (container 3)  ← message G, H, I
             (all in the same group — Redis distributes automatically)
```
