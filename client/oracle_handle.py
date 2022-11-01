from typing import List
import kubernetes
from kubernetes.client.models.v1_stateful_set import V1StatefulSet
from kubernetes.client.models.v1_pod import V1Pod
from .kubectl import KubectlClient


class OracleHandle:

    def __init__(self, kubectl_client: KubectlClient, k8s_client: kubernetes.client.ApiClient,
                 namespace: str):
        self.kubectl_client = kubectl_client
        self.k8s_client = k8s_client
        self.namespace = namespace

    def get_stateful_sets(self) -> List[V1StatefulSet]:
        '''Get all stateful sets in the namespace
        
        Returns:
            list[V1StatefulSet]
        '''
        appv1 = kubernetes.client.AppsV1Api(self.k8s_client)
        return appv1.list_namespaced_stateful_set(self.namespace).items

    def get_pods_in_stateful_set(self, stateful_set: V1StatefulSet) -> List[V1Pod]:
        '''Get all pods in the stateful set
        
        Args:
            stateful_set: stateful set object in kubernetes
        
        Returns:
            list[V1Pod]
        '''

        all_pods: List[V1Pod] = kubernetes.client.CoreV1Api(self.k8s_client).list_namespaced_pod(
            self.namespace).items

        for pod in all_pods:
            for reference in pod.metadata.owner_references:
                if reference.uid == stateful_set.metadata.uid:
                    yield pod