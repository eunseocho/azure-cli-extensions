import subprocess
import time
import yaml
from kubernetes import client, config, utils 

from azure.cli.command_modules.acs.custom import (
    aks_create,
    aks_get_credentials,
)
from azure.cli.command_modules.acs._client_factory import cf_managed_clusters

containerapp_template = {'apiVersion': 0, 'kind': 0, 'metadata': 0, 'annotations': 0, 'controller-gen.kubebuilder.io/version': 0, 
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
'acceptedNames': 0, 'conditions': 0, 'storedVersions': 0, 'namespace':0}

dapr_template = {'apiVersion': 0, 'kind': 0, 'metadata': 0, 'annotations': 0, 
'controller-gen.kubebuilder.io/version': 0, 'meta.helm.sh/release-name': 0, 
'meta.helm.sh/release-namespace': 0, 'labels': 0, 'app.kubernetes.io/managed-by': 0, 
'creationTimestamp': 0, 'name': 0, 'spec': 0, 'group': 0, 'names': 0, 
'listKind': 0, 'plural': 0, 'singular': 0, 'scope': 0, 'versions': 0, 
'schema': 0, 'openAPIV3Schema': 0, 'description': 0, 'properties': 0, 
'type': 0, 'ignoreErrors': 0, 'initTimeout': 0, 'items': 0, 'secretRef': 0, 
'value': 0, 'required': 0, 'scopes': 0, 'secrets': 0, 'version': 0, 'status': 0, 
'served': 0, 'storage': 0, 'subresources': 0, 'acceptedNames': 0, 'conditions': 0, 
'storedVersions': 0}

def _check_system_requirements():
    satisfied = True

    check_helm = subprocess.run("helm version --short".split(), check=True, capture_output=True, shell=True)
    if check_helm.returncode != 0:
        print("Please install helm")
        print("https://helm.sh/docs/intro/install/")
        satisfied = False
    else:
        version = check_helm.stdout
        version = version.decode('ascii')
        if int(version[1]) >= 3 and int(version[3]) >= 1:
            print("helm is installed")
        else:
            print("helm needs to be upgraded")
            print("https://helm.sh/docs/helm/helm_upgrade/")
            satisfied = False

    check_kubectl = subprocess.run("kubectl version".split(), check=True, capture_output=True, shell=True)
    if check_kubectl.returncode != 0:
        print("Please install kubectl")
        print("https://kubernetes.io/docs/tasks/tools/#kubectl")
        satisfied = False
    else:
        # add the version check here
        print("kubectl is installed")

    return satisfied

# creates a new AKS cluster and install k4apps and such
# TODO: configure the cluster the same way ACA did -- do I need to manually set the number of nodes and such?
def _configure_aks_cluster(cmd, resource_group_name, cluster, create_cluster):
    if _check_system_requirements() == False:
        return False

    client = cf_managed_clusters(cmd.cli_ctx)

    if create_cluster == True:
        print(f"Creating a new AKS cluster named {cluster}")
        aks_create(
            cmd, 
            client=client, 
            resource_group_name=resource_group_name, 
            name=cluster, 
            ssh_key_value=None, 
            no_ssh_key=True
        )
        # TODO: need to add a check whether the cluster's created or not, so it only proceeds when the cluster exists
        print("Connecting kubectl to the new cluster")
    else:
        print(f"Ejecting into the cluster {cluster} under the resource group {resource_group_name}")
        print("Connecting kubectl to the provided cluster")

    aks_get_credentials(cmd, client=client, name=cluster, resource_group_name=resource_group_name)

    _install_cluster_requirements()

    return True

def _install_cluster_requirements():
    config.load_kube_config()

    v1= client.CoreV1Api()
    res = v1.list_namespace(watch=False)
    installed_namespaces = set([i.metadata.name for i in res.items])

    if "keda" in installed_namespaces:
        print("keda is installed")
    else:
        print("installing keda")
        v1.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name="keda")))
        subprocess.run("helm repo add kedacore https://kedacore.github.io/charts".split(), stderr=subprocess.STDOUT, shell=True)
        subprocess.run("helm repo update".split(), stderr=subprocess.STDOUT, shell=True)
        subprocess.run("helm install keda kedacore/keda --namespace keda".split(), stderr=subprocess.STDOUT, shell=True)

    if "dapr-system" in installed_namespaces:
        print("dapr is installed")
    else:
        print("installing dapr")
        v1.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name="dapr-system")))
        subprocess.run("helm repo add dapr https://dapr.github.io/helm-charts/".split(), stderr=subprocess.STDOUT, shell=True)
        subprocess.run("helm repo update".split(), stderr=subprocess.STDOUT, shell=True)
        subprocess.run("helm install dapr dapr/dapr --namespace dapr-system".split(), stderr=subprocess.STDOUT, shell=True)

    if "k8se-system" in installed_namespaces:
        # upgrading
        print("upgrading k4apps")
        subprocess.run(
            "helm upgrade k8se oci://mcr.microsoft.com/k8se/chart --version 1.0.35 --namespace k8se-system --create-namespace --set webhooks.enabled=false --set dapr.enabled=false --set keda.enabled=false".split(), 
            stderr=subprocess.STDOUT, 
            shell=True,
        )  
    else:     
        print("installing k4apps")
        subprocess.run(
            "helm install k8se oci://mcr.microsoft.com/k8se/chart --version 1.0.35 --namespace k8se-system --create-namespace --set webhooks.enabled=false --set dapr.enabled=false --set keda.enabled=false".split(), 
            stderr=subprocess.STDOUT, 
            shell=True,
        )

def _convert_deploy_dapr_component(json_dict):
    name = json_dict["name"]

    yaml_dict = {}
    yaml_dict["apiVersion"] = "k8se.microsoft.com/v1alpha1"
    yaml_dict["kind"] = "DaprComponent"
    yaml_dict["metadata"] = {"name":name, "namespace":"k8se-apps"}

    # not including secrets for now
    if "secrets" in json_dict["properties"]:
        json_dict["properties"].pop("secrets")

    yaml_dict["spec"] = {"type": json_dict["properties"]["componentType"], "metadata":{}}
    yaml_dict["spec"]["metadata"] = json_dict["properties"]

    _convert_crd(yaml_dict, dapr_template, name)

    # _deploy_k8se(yaml_dict)

def _convert_deploy_app(cmd, json_dict, app_name, secrets, deploy=False):
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

    _convert_crd(yaml_dict, containerapp_template, app_name)

    if deploy:
        # TODO: need to debug the _deploy_k8se function
        # _deploy_k8se(yaml_dict)
        file_name = app_name + ".yaml"
        subprocess.run("kubectl apply -f {file_name}", stderr=subprocess.STDOUT, shell=True)

        time.sleep(3)

        ip = subprocess.run("kubectl -n k8se-system get svc k8se-envoy -o jsonpath=\"{.status.loadBalancer.ingress[0].ip}\"".split(), stdout=subprocess.PIPE, text=True, shell=True)
        ip = ip.stdout.strip('\"')
        subprocess.run(f"curl -H \"Host: {app_name}.k4apps-example.io\" {ip} -v", stderr=subprocess.STDOUT, shell=True)

def _convert_crd(crd_dict, template, name):
    _dfs(crd_dict, template)

    # create and load an empty yaml file
    file_name = name + ".yaml"
    outfile = open(file_name, "w+")

    yaml.dump(crd_dict, outfile, allow_unicode=True)

    # dump into the yaml file created
    print(f"yaml file for the app {name} created")
    print()
    print(yaml.dump(crd_dict, indent=4, default_flow_style=False))
    print("-----------------------------------------------------------------------")

def _dfs(json_dict, to_crd_map):
    if json_dict == None or type(json_dict) == bool or type(json_dict) == str or type(json_dict) == int:
        return
    elif type(json_dict) == list:
        for i in json_dict:
            _dfs(i, to_crd_map)
    else:
        to_delete = []
        to_replace = []

        for key in json_dict:
            if key in to_crd_map:
                if to_crd_map[key] == 1:
                    json_dict[key] = str(json_dict[key])
                elif type(to_crd_map[key]) == str:
                    to_replace.append(key)
                _dfs(json_dict[key], to_crd_map)
            else:
                to_delete.append(key)
        
        for k in to_replace:
            v = json_dict[k]
            json_dict[to_crd_map[k]] = v
            json_dict.pop(k)
        
        for k in to_delete:
            json_dict.pop(k)

def _deploy_k8se(crd_dict):
    config.load_kube_config()
    k8s_app = client.AppsV1Api()
    resp = k8s_app.create_namespaced_deployment(body=crd_dict, namespace="k8se-apps")
    print("Deployment created. status='%s'" % resp.metadata.name)