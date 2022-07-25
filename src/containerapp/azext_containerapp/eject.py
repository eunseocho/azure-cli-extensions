import subprocess
import time
import yaml
from kubernetes import client, config, utils 

from azure.cli.command_modules.acs.custom import (
    aks_create,
    aks_get_credentials,
)
from azure.cli.command_modules.acs._client_factory import cf_managed_clusters

# creates a new AKS cluster and install k4apps and such
def _configure_aks_cluster(cmd, resource_group_name, cluster, create_cluster):
    if check_system_requirements() == False:
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
        print("Connecting kubectl to the new cluster")
    else:
        print(f"Ejecting into the cluster {cluster} under the resource group {resource_group_name}")
        print("Connecting kubectl to the provided cluster")

    aks_get_credentials(cmd, client=client, name=cluster, resource_group_name=resource_group_name)

    install_cluster_requirements()

    return True
    # TODO: configure the cluster the same way ACA did -- do I need to manually set the number of nodes and such?

def _convert_deploy_app(cmd, json_dict, app_name, secrets, to_crd, deploy=False):
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

    dfs(yaml_dict["spec"]["configuration"], to_crd)
    dfs(yaml_dict["spec"]["template"], to_crd)

    # create and load an empty yaml file
    file_name = app_name + ".yaml"
    outfile = open(file_name, "w+")

    yaml.dump(yaml_dict, outfile, allow_unicode=True)

    # dump into the yaml file created
    print(f"yaml file for the app {app_name} created")
    print()
    print(yaml.dump(yaml_dict, indent=4, default_flow_style=False))
    print("-----------------------------------------------------------------------")

    if deploy:
        print(f"deploying the app {app_name}")
        subprocess.run(f"kubectl apply -f {file_name}".split(), stderr=subprocess.STDOUT, shell=True)
        
        time.sleep(3)

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

def check_system_requirements():
    satisfied = True

    check_helm = subprocess.run("helm version --short".split(), check=True, capture_output=True)
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

    check_kubectl = subprocess.run("kubectl version".split(), check=True, capture_output=True)
    if check_kubectl.returncode != 0:
        print("Please install kubectl")
        print("https://kubernetes.io/docs/tasks/tools/#kubectl")
        satisfied = False
    else:
        # check the version check here
        print("kubectl is installed")

    return satisfied

def install_cluster_requirements():
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