import subprocess
import time
import yaml
from kubernetes import client, config

from azure.cli.command_modules.acs.custom import (
    aks_create,
    aks_get_credentials,
    aks_show,
)
from azure.cli.command_modules.acs._client_factory import cf_managed_clusters

REQUIRED_MIN_HELM_VERSION = "3.1"
REQUIRED_MIN_KUBERNETES_VERSION = "1.12"

K4APPS_HELM_CHART = "oci://mcr.microsoft.com/k8se/chart"
K4APPS_CHART_RELEASE_NAME = "k8se"
K4APPS_VERSION = "1.0.35"
K4APPS_NAMESPACE = "k8se-system"
# genCert to allow self-signed certificate
K4APPS_CHART_FLAGS = "--set webhooks.enabled=false --set dapr.enabled=false --set keda.enabled=false --set containerAppController.enabled=true --set genCert=true"

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
'componentType': 'type', 'ignoreErrors': 0, 'initTimeout': 0, 'items': 0, 'secretRef': 0, 
'value': 0, 'required': 0, 'scopes': 0, 'secrets': 0, 'version': 0, 'status': 0, 
'served': 0, 'storage': 0, 'subresources': 0, 'acceptedNames': 0, 'conditions': 0, 
'storedVersions': 0}

def _meet_system_requirements():
    config.load_kube_config()

    satisfied = True

    check_helm = subprocess.run("helm version --short".split(), check=True, capture_output=True, shell=True)
    if check_helm.returncode != 0:
        print("Please install helm")
        print("https://helm.sh/docs/intro/install/")
        satisfied = False
    else:
        version = check_helm.stdout
        version = version.decode('ascii')
        if int(version[1]) >= int(REQUIRED_MIN_HELM_VERSION[0]) and int(version[3]) >= int(REQUIRED_MIN_HELM_VERSION[2]):
            print("helm is installed")
        else:
            print("helm needs to be upgraded")
            print("https://helm.sh/docs/helm/helm_upgrade/")
            satisfied = False

    # TODO: Just check for the client version
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
def _configure_aks_cluster(cmd, resource_group_name, cluster, create_new_cluster):
    client = cf_managed_clusters(cmd.cli_ctx)

    cluster_created = False
    if create_new_cluster:
        print(f"Creating a new AKS cluster named {cluster}", end = " ")
        # subprocess.run(f"az aks create --name {cluster} --resource-group {resource_group_name}".split(), stderr=subprocess.STDOUT, shell=True)
        aks_create(
            cmd, 
            client=client, 
            resource_group_name=resource_group_name, 
            name=cluster, 
            ssh_key_value=None, 
            no_ssh_key=True
        )

        time.sleep(10)

        # TODO: Need to debug; doesn't show the progress dots properly
        for _ in range(30):
            if aks_show(cmd, client, resource_group_name, cluster).provisioning_state == "Succeeded":
                print(". ------------ Cluster is created.")
                cluster_created = True
                print("Connecting kubectl to the new cluster")
                break
            
            print(".", end = " ")

            time.sleep(10)

    else:
        print(f"Ejecting into the cluster {cluster} under the resource group {resource_group_name}")
        print("Connecting kubectl to the provided cluster")

    # TODO: Need to take an appropriate action when it didn't complete creating the cluster
    if create_new_cluster and not cluster_created:
        print(f"A new AKS cluster creation is not completed. Try ejecting into {cluster} later again.")
        return False

    # subprocess.run(f"az aks get-credentials --name {cluster} --resource-group {resource_group_name}".split(), stderr=subprocess.STDOUT, shell=True)
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
        print("Installing keda")
        v1.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name="keda")))
        subprocess.run("helm repo add kedacore https://kedacore.github.io/charts".split(), stderr=subprocess.STDOUT, shell=True)
        subprocess.run("helm repo update".split(), stderr=subprocess.STDOUT, shell=True)
        subprocess.run("helm install keda kedacore/keda --namespace keda".split(), stderr=subprocess.STDOUT, shell=True)

    if "dapr-system" in installed_namespaces:
        print("dapr is installed")
    else:
        print("Installing dapr")
        v1.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name="dapr-system")))
        subprocess.run("helm repo add dapr https://dapr.github.io/helm-charts/".split(), stderr=subprocess.STDOUT, shell=True)
        subprocess.run("helm repo update".split(), stderr=subprocess.STDOUT, shell=True)
        subprocess.run("helm install dapr dapr/dapr --namespace dapr-system".split(), stderr=subprocess.STDOUT, shell=True)

    if "k8se-system" in installed_namespaces:
        # upgrading
        print("Upgrading k4apps")
        subprocess.run(
            f"helm upgrade {K4APPS_CHART_RELEASE_NAME} {K4APPS_HELM_CHART} --version {K4APPS_VERSION} --namespace {K4APPS_NAMESPACE} --create-namespace {K4APPS_CHART_FLAGS}".split(), 
            stderr=subprocess.STDOUT, 
            shell=True,
        )  
    else:     
        print("Installing k4apps")
        subprocess.run(
            f"helm install {K4APPS_CHART_RELEASE_NAME} {K4APPS_HELM_CHART} --version {K4APPS_VERSION} --namespace {K4APPS_NAMESPACE} --create-namespace {K4APPS_CHART_FLAGS}".split(), 
            stderr=subprocess.STDOUT, 
            shell=True,
        )

def _convert_deploy_dapr_component(json_dict, secrets, deploy):
    name = json_dict["name"]

    yaml_dict = {}
    yaml_dict["apiVersion"] = "k8se.microsoft.com/v1alpha1"
    yaml_dict["kind"] = "DaprComponent"
    yaml_dict["metadata"] = {"name":name, "namespace":"k8se-apps"}

    yaml_dict["spec"] = json_dict["properties"]

    if "secrets" in yaml_dict["spec"]:
        yaml_dict["spec"]["secrets"] = secrets

    yaml_dict["spec"]["metadata"] = json_dict["properties"]["metadata"]

    _convert_crd(yaml_dict, dapr_template, name)

    if deploy:
        # subprocess.run(f"kubectl apply -f {file_name}", stderr=subprocess.STDOUT, shell=True)
        _deploy(yaml_dict, name)

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
        # subprocess.run(f"kubectl apply -f {file_name}".split(), stderr=subprocess.STDOUT, shell=True)
        _deploy(yaml_dict, app_name)

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

    return file_name

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

def _deploy(app_yaml, app_name):
    # kubectl apply -f app.yaml

    config.load_kube_config()

    yaml_body = app_yaml

    try:
        client.CustomObjectsApi().get_namespaced_custom_object(
            group="k8se.microsoft.com",
            version="v1alpha1",
            namespace="k8se-apps",
            plural="containerapps",
            name=app_name,
        )

        # Couldn't get this to work due to resourceVersion error
        # resp = client.CustomObjectsApi().replace_namespaced_custom_object(
        #     group="k8se.microsoft.com",
        #     version="v1alpha1",
        #     namespace="k8se-apps",
        #     plural="containerapps",
        #     name=app_name,
        #     body=yaml_body,
        # )

        client.CustomObjectsApi().delete_namespaced_custom_object(
            group="k8se.microsoft.com",
            version="v1alpha1",
            namespace="k8se-apps",
            plural="containerapps",
            name=app_name,
        )

        resp = client.CustomObjectsApi().create_namespaced_custom_object(
            group="k8se.microsoft.com",
            version="v1alpha1",
            namespace="k8se-apps",
            plural="containerapps",
            body=yaml_body,
        )
        print("Deployment updated for %s" % resp["metadata"]["name"])

    except client.ApiException:
        resp = client.CustomObjectsApi().create_namespaced_custom_object(
            group="k8se.microsoft.com",
            version="v1alpha1",
            namespace="k8se-apps",
            plural="containerapps",
            body=yaml_body,
        )
        print("Deployment created for %s" % resp["metadata"]["name"])
