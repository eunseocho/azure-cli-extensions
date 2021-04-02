# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
#
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------


def cf_cloud_service_cl(cli_ctx, *_):
    from azure.cli.core.commands.client_factory import get_mgmt_service_client
    from azure.mgmt.compute import ComputeManagementClient
    return get_mgmt_service_client(cli_ctx,
                                   ComputeManagementClient)


def cf_cloud_service_role_instance(cli_ctx, *_):
    return cf_cloud_service_cl(cli_ctx).cloud_service_role_instances


def cf_cloud_service_role(cli_ctx, *_):
    return cf_cloud_service_cl(cli_ctx).cloud_service_roles


def cf_cloud_service(cli_ctx, *_):
    return cf_cloud_service_cl(cli_ctx).cloud_services


def cf_cloud_service_update_domain(cli_ctx, *_):
    return cf_cloud_service_cl(cli_ctx).cloud_services_update_domain
