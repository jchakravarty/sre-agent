#!/usr/bin/env python3
"""
Example of how Harness CD pipeline would integrate with the SRE Agent
to get intelligent Kubernetes and Karpenter configuration suggestions.
"""

import json
import requests
from typing import Dict, Any

# Example Harness pipeline integration
class HarnessIntegration:
    def __init__(self, sre_agent_url: str):
        self.sre_agent_url = sre_agent_url
        self.suggestion_endpoint = f"{sre_agent_url}/suggest"
        self.quality_gate_endpoint = f"{sre_agent_url}/gate"
    
    def get_scaling_suggestion(self, app_name: str, environment: str, deployment_name: str) -> Dict[str, Any]:
        """
        Get intelligent scaling configuration from SRE Agent
        This would be called from Harness pipeline before deployment
        """
        payload = {
            "suggestion_type": "kubernetes_scaling",
            "application": {
                "name": app_name,
                "version": "1.0.0",
                "team": "platform"
            },
            "deployment_context": {
                "environment": environment,
                "deployment_name": deployment_name,
                "architecture": "amd64",
                "cluster_name": f"eks-{environment}",
                "namespace": f"{app_name}-{environment}"
            }
        }
        
        response = requests.post(
            self.suggestion_endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"SRE Agent returned {response.status_code}: {response.text}")
    
    def check_quality_gate(self, app_name: str, commit_sha: str, artifact_id: str) -> Dict[str, Any]:
        """
        Check quality gate before deployment
        """
        payload = {
            "application": {
                "name": app_name,
                "commit_sha": commit_sha,
                "artifact_id": artifact_id
            }
        }
        
        response = requests.post(
            self.quality_gate_endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Quality gate check failed: {response.text}")
    
    def generate_k8s_manifests(self, app_name: str, environment: str, deployment_name: str) -> Dict[str, str]:
        """
        Generate Kubernetes manifests with intelligent scaling configuration
        """
        # Get AI-powered scaling suggestion
        suggestion = self.get_scaling_suggestion(app_name, environment, deployment_name)
        
        if suggestion['suggestion_source'] == 'llm_validated':
            print("✅ Using AI-powered scaling configuration")
        else:
            print("⚠️  Using static fallback configuration")
        
        scaling_config = suggestion['suggestion']
        
        # Generate HPA manifest
        hpa_manifest = self._generate_hpa_manifest(scaling_config['hpa'])
        
        # Generate Karpenter NodePool manifest
        karpenter_manifest = self._generate_karpenter_manifest(scaling_config['karpenter'])
        
        # Generate Deployment manifest with resource limits
        deployment_manifest = self._generate_deployment_manifest(
            app_name, 
            scaling_config['hpa']['resources']
        )
        
        return {
            "hpa.yaml": hpa_manifest,
            "karpenter.yaml": karpenter_manifest,
            "deployment.yaml": deployment_manifest
        }
    
    def _generate_hpa_manifest(self, hpa_config: Dict[str, Any]) -> str:
        """Generate HPA manifest based on AI suggestion"""
        return f"""
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {hpa_config['scaleTargetRefName']}-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {hpa_config['scaleTargetRefName']}
  minReplicas: {hpa_config['minReplicas']}
  maxReplicas: {hpa_config['maxReplicas']}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {hpa_config['targetCPUUtilizationPercentage']}
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
"""
    
    def _generate_karpenter_manifest(self, karpenter_config: Dict[str, Any]) -> str:
        """Generate Karpenter NodePool manifest"""
        return f"""
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: default
spec:
  template:
    metadata:
      labels:
        intent: apps
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["{karpenter_config['kubernetes.io/arch']}"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["{karpenter_config['karpenter.sh/capacity-type']}"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m5.large", "m5.xlarge", "m5.2xlarge"]
      nodeClassRef:
        apiVersion: karpenter.k8s.aws/v1beta1
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
"""
    
    def _generate_deployment_manifest(self, app_name: str, resources: Dict[str, Any]) -> str:
        """Generate Deployment manifest with resource limits"""
        return f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}
spec:
  selector:
    matchLabels:
      app: {app_name}
  template:
    metadata:
      labels:
        app: {app_name}
    spec:
      containers:
      - name: {app_name}
        image: {app_name}:latest
        resources:
          requests:
            cpu: {resources['cpuRequest']}
            memory: {resources['memoryRequest']}
          limits:
            cpu: {resources['cpuLimit']}
            memory: {resources['memoryLimit']}
        ports:
        - containerPort: 8080
"""

# Example usage in Harness pipeline
def main():
    # Initialize integration
    harness = HarnessIntegration("https://sre-agent.company.com")
    
    # Example: Deploy microservice to production
    app_name = "user-service"
    environment = "prod"
    deployment_name = "user-service-prod"
    commit_sha = "abc123"
    artifact_id = "user-service:v1.2.3"
    
    try:
        # Step 1: Check quality gate
        print("🔍 Checking quality gate...")
        quality_result = harness.check_quality_gate(app_name, commit_sha, artifact_id)
        
        if quality_result['status'] != 'SUCCESS':
            print(f"❌ Quality gate failed: {quality_result['message']}")
            return
        
        print("✅ Quality gate passed")
        
        # Step 2: Generate intelligent K8s manifests
        print("🤖 Generating intelligent Kubernetes manifests...")
        manifests = harness.generate_k8s_manifests(app_name, environment, deployment_name)
        
        # Step 3: Apply manifests (this would be done by Harness)
        for filename, content in manifests.items():
            print(f"📄 Generated {filename}:")
            print(content)
            print("-" * 50)
        
        print("🚀 Ready for deployment!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
