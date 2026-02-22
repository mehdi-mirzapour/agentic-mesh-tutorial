# Deployment Strategy: Independent Agent Groups

To achieve a resilient and scalable system, each agent group (Coordinator, Specialists, and Aggregator) is deployed as an independent service. This allows us to scale individual specialists based on workload (e.g., doubling the number of Grammar agents without affecting the Tone agents).

## Docker Deployment (Microservices)

Using the provided `docker-compose.yml`, you can launch the entire mesh as separate containers:

```bash
docker-compose up --build -d
```

### Scaling a Specific Group
If you notice the grammar queue (`doc.review.grammar`) is backing up, you can scale just that service:

```bash
docker-compose up -d --scale grammar-agent=3
```

---

## Kubernetes Deployment (AKS ready)

Each group should be defined as a separate **Deployment**. This ensures that if one agent crashes, Kubernetes will restart it without affecting the others.

### Target Manifest Structure

1.  **Redis Service**: A central Redis instance or cluster.
2.  **Coordinator Deployment**: Single replica (usually enough).
3.  **Specialist Deployments**: Multiple deployments (one per `--type`).
4.  **Aggregator Deployment**: Scalable based on suggestion volume.

### Example Deployment Template (General)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: specialist-grammar
spec:
  replicas: 2
  selector:
    matchLabels:
      app: specialist-grammar
  template:
    metadata:
      labels:
        app: specialist-grammar
    spec:
      containers:
      - name: agent
        image: your-registry/agentic-mesh:latest
        args: ["specialist", "--type", "grammar"]
        env:
        - name: REDIS_HOST
          value: "redis-service"
```

## Benefits of Separate Deployment

1.  **Isolation**: A memory leak or crash in the `tone` specialist doesn't stop the `grammar` check.
2.  **Granular Scaling**: Specialists performing heavy LLM calls can be assigned more resources or replicas.
3.  **Version Independent**: You can update the `coordinator` without restarting the `specialists`.
4.  **Monitoring**: Easier to track Redis stream consumption per specialist group via independent logs.
