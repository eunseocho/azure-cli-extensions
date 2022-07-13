import subprocess
import yaml

from azure.cli.command_modules.acs.custom import (
    aks_create,
    k8s_get_credentials,
)
from azure.cli.command_modules.acs._client_factory import cf_container_services, get_container_service_client

# creates a new AKS cluster and install k4apps and such
def _configure_aks_cluster(cmd, resource_group_name, cluster, create_cluster):
    client = cf_container_services(cmd.cli_ctx)

    # print(cmd.cli_ctx.data)
    if create_cluster == True:
        print(f"Creating a new AKS cluster named {cluster}")
        # subprocess.run(["az", "aks", "create", "--resource-group", resource_group_name, "--name", cluster], stderr=subprocess.STDOUT, shell=True)
        aks_create(cmd, client=client, resource_group_name=resource_group_name, name=cluster, ssh_key_value=None, no_ssh_key=True)
        print("Connecting kubectl to the new cluster")
    else:
        print(f"Ejecting into the cluster {cluster} under the resource group {resource_group_name}")
        print("Connecting kubectl to the provided cluster")

    k8s_get_credentials(cmd, client=client, name=cluster, resource_group_name=resource_group_name)
    # subprocess.run(f"az aks get-credentials --resource-group {resource_group_name} --name {cluster}", stderr=subprocess.STDOUT, shell=True)

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

def _convert_deploy_app(json_dict, app_name, secrets, to_crd, deploy=False):
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