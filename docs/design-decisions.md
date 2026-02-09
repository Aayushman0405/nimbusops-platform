```md
# Design Decisions & Tradeoffs ⚖️

---

## Why Not HPA?

HPA:
- Reactive
- Metric-limited
- No cost awareness
- No explainability

NimbusOps:
- Predictive
- Multi-metric
- Cost-aware
- Policy-driven

---

## Why CephFS RWX?

- Multiple pods need shared access
- Model registry consistency
- No object-store complexity
- POSIX semantics

---

## Why Custom Operators?

- CRDs express intent
- GitOps friendly
- Kubernetes-native workflows
- Clear audit trail

---

## Why Separate Control Planes?

- Failure isolation
- Security boundaries
- Independent scaling
- Clear ownership

---

## Why Prometheus Over Cloud Metrics?

- Vendor neutral
- Fine-grained queries
- Custom metrics
- Predictive modeling

---

## Why GitHub Actions?

- Full control
- Self-hosted runners
- No SaaS lock-in
- Infra-level CI/CD
