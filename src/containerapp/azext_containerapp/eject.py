import subprocess
import yaml
from azure.cli.command_modules.acs.base_decorator import ContainerServiceClient

from azure.cli.command_modules.acs.custom import (
    aks_create,
    k8s_get_credentials,
)
from azure.cli.command_modules.acs._client_factory import get_container_service_client

from azure.cli.core.profiles._shared import get_client_class, ResourceType

# creates a new AKS cluster and install k4apps and such
def _configure_aks_cluster(cmd, resource_group_name, cluster, create_cluster):
    # client = get_container_service_client(cmd.cli_ctx)
    # print(cmd.cli_ctx.data)
    if create_cluster == True:
        print(f"Creating a new AKS cluster named {cluster}")
        subprocess.run(["az", "aks", "create", "--resource-group", resource_group_name, "--name", cluster], stderr=subprocess.STDOUT, shell=True)
        # aks_create(cmd, client=client, resource_group_name=resource_group_name, name=cluster, ssh_key_value=None, no_ssh_key=True)
        print("Connecting kubectl to the new cluster")
    else:
        print(f"Ejecting into the cluster {cluster} under the resource group {resource_group_name}")
        print("Connecting kubectl to the provided cluster")
    
    # k8s_get_credentials(cmd, resource_group_name=resource_group_name, name=cluster)
    subprocess.run(f"az aks get-credentials --resource-group {resource_group_name} --name {cluster}", stderr=subprocess.STDOUT, shell=True)

    # TODO: configure the cluster the same way ACA did -- do I need to manually set the number of nodes and such?

    print("installing keda")
    subprocess.run(["kubectl", "create", "namespace", "keda"], stderr=subprocess.STDOUT, shell=True)
    subprocess.run("helm repo add kedacore https://kedacore.github.io/charts".split(), stderr=subprocess.STDOUT, shell=True)
    subprocess.run("helm repo update".split(), stderr=subprocess.STDOUT, shell=True)
    subprocess.run(["helm", "install", "keda", "kedacore/keda", "--namespace", "keda"], stderr=subprocess.STDOUT, shell=True)

    print("installing dapr")
    subprocess.run("helm repo add dapr https://dapr.github.io/helm-charts/".split(), stderr=subprocess.STDOUT, shell=True)
    subprocess.run("helm repo update".split(), stderr=subprocess.STDOUT, shell=True)
    subprocess.run("kubectl create namespace dapr-system".split(), stderr=subprocess.STDOUT, shell=True)
    subprocess.run("helm install dapr dapr/dapr --namespace dapr-system".split(), stderr=subprocess.STDOUT, shell=True)

    # installing this chart to download k4apps
    # need to add a condition where I can upgrade the charts if it exists already
    print("installing k4apps")
    subprocess.run(
        "helm install k8se oci://mcr.microsoft.com/k8se/chart --version 1.0.35 --namespace k8se-system --create-namespace --set webhooks.enabled=false --set dapr.enabled=false --set keda.enabled=false".split(), 
        stderr=subprocess.STDOUT, 
        shell=True,
    )

def _convert_deploy_app(json_dict, app_name, secrets=None, deploy=False):
    yaml_dict = {}

    # hard coded 
    # TODO: will the apps to be ejected always ContainerApp type?
    yaml_dict["apiVersion"] = "k8se.microsoft.com/v1alpha1"
    yaml_dict["kind"] = "ContainerApp"
    yaml_dict["metadata"] = {"name":app_name, "namespace":"k8se-apps"}
    yaml_dict["spec"] = {"configuration":{}, "template":{}}

    yaml_dict["spec"]["configuration"] = json_dict["properties"]["configuration"]
    yaml_dict["spec"]["template"] = json_dict["properties"]["template"]

    # set secret 
    yaml_dict["spec"]["configuration"]["secrets"] = secrets

    to_crd = {'apiVersion': 0, 'kind': 0, 'metadata': 0, 'annotations': 0, 'controller-gen.kubebuilder.io/version': 0, 
    'meta.helm.sh/release-name': 0, 'meta.helm.sh/release-namespace': 0, 'labels': 0, 'app.kubernetes.io/managed-by': 0, 'creationTimestamp': 0, 
    'name': 0, 'spec': 0, 'group': 0, 'names': 0, 'listKind': 0, 'plural': 0, 'singular': 0, 'scope': 0, 'versions': 0, 'schema': 0, 
    'openAPIV3Schema': 0, 'description': 0, 'properties': 0, 'type': 0, 'configuration': 0, 'activeRevisionsMode': 0, 'default': 0, 'authConfig': 0, 
    'defaultProvider': 0, 'enabled': 0, 'secretRef': 0, 'dapr': 0, 'appID': 0, 'appPort': 0, 'format': 0, 'appProtocol': 0, 'enableApiLogging': 0, 
    'httpMaxRequestSize': 0, 'httpReadBufferSize': 0, 'logLevel': 0, 'required': 0, 'identity': 0, 'authenticationEndpointEnabled': 0, 'identities': 0, 
    'items': 0, 'authenticationEndpoint': 0, 'certificateName': 0, 'clientId': 0, 'principalId': 0, 'resourceId': 0, 'secretUrl': 0, 'tenantId': 0, 
    'identityHeader': 0, 'secretName': 0, 'siteName': 0, 'ingress': 0, 'allowInsecure': 0, 'customDomains': 0, 'certificateRef': 0, 'hostName': 0, 
    'external': 0, 'targetPort': 0, 'traffic': 0, 'label': 0, 'latestRevision': 0, 'weight': 'percent', 'revisionName': 0, 'transport': 0, 'registries': 0, 
    'passwordSecretRef': 0, 'server': 0, 'username': 0, 'secrets': 0, 'value': 0, 'template': 0, 'containers': 0, 'args': 0, 'command': 0, 'env': 0, 
    'image': 0, 'probes': 0, 'livenessProbe': 0, 'exec': 0, 'failureThreshold': 0, 'httpGet': 0, 'host': 0, 'httpHeaders': 0, 'path': 0, 'port': 0, 
    'anyOf': 0, 'x-kubernetes-int-or-string': 0, 'scheme': 0, 'initialDelaySeconds': 0, 'periodSeconds': 0, 'successThreshold': 0, 'tcpSocket': 0, 
    'terminationGracePeriodSeconds': 0, 'timeoutSeconds': 0, 'readinessProbe': 0, 'startupProbe': 0, 'resources': 0, 'cpu': 1, 'ephemeralStorage': 'ephemeral-storage', 
    'memory': 1, 'components': 0, 'ignoreErrors': 0, 'initTimeout': 0, 'scopes': 0, 'version': 0, 'revisionSuffix': 0, 'scale': 0, 'maxReplicas': 0, 
    'minReplicas': 0, 'rules': 0, 'auth': 0, 'triggerParameter': 0, 'additionalProperties': 0, 'storage': 0, 'mounts': 0, 'containerName': 0, 
    'volumeMounts': 0, 'mountPath': 0, 'mountPropagation': 0, 'readOnly': 0, 'subPath': 0, 'subPathExpr': 0, 'volumes': 0, 'azureFileVolumeSource': 0, 
    'shareName': 0, 'status': 0, 'containerAppProvisioningState': 0, 'containerAppProvisoningError': 0, 'currentActiveRevisionName': 0, 
    'lastConfigurationState': 0, 'latestCreatedRevisionName': 0, 'latestReadyRevisionName': 0, 'observedGeneration': 0, 'served': 0, 'subresources': 0, 
    'acceptedNames': 0, 'conditions': 0, 'storedVersions': 0}

    dfs(yaml_dict["spec"]["configuration"], to_crd)
    dfs(yaml_dict["spec"]["template"], to_crd)

    # create and load an empty yaml file
    file_name = app_name + ".yaml"
    outfile = open(file_name, "w+")

    # dump into the yaml file created
    yaml_obj = yaml.dump(yaml_dict, outfile, allow_unicode=True)

    print(f"yaml file for the app {app_name} is created")

    print(yaml_obj)

    if deploy:
        print(f"deploying the app {app_name}")
        subprocess.run(f"kubectl apply -f {file_name}".split(), stderr=subprocess.STDOUT, shell=True)
        
        ip = subprocess.run("kubectl -n k8se-system get svc k8se-envoy -o jsonpath=\"{.status.loadBalancer.ingress[0].ip}\"".split(), stdout=subprocess.PIPE, text=True, shell=True)
        ip = ip.stdout.strip('\"')
        subprocess.run(f"curl -H \"Host: {app_name}.k4apps-example.io\" {ip} -v", stderr=subprocess.STDOUT, shell=True)

def dfs(json_dict, to_crd_map):
    if json_dict == None or type(json_dict) == bool or type(json_dict) == str or type(json_dict) == int:
        return
    elif type(json_dict) == list:
        for i in json_dict:
            dfs(i, to_crd_map)
    else:
        to_delete = []
        to_replace = []

        for key in json_dict:
            if key in to_crd_map:
                if to_crd_map[key] == 1:
                    json_dict[key] = str(json_dict[key])
                elif type(to_crd_map[key]) == str:
                    to_replace.append(key)
                dfs(json_dict[key], to_crd_map)
            else:
                to_delete.append(key)
        
        for k in to_replace:
            v = json_dict[k]
            json_dict[to_crd_map[k]] = v
            json_dict.pop(k)
        
        for k in to_delete:
            json_dict.pop(k)