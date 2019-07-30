# ------------------------------------------------------------------------
# Copyright 2018 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Description:  Google Cloud Platform - SAP Deployment Functions
# Build Date:   Fri Mar 15 13:25:46 GMT 2019
# ------------------------------------------------------------------------

"""Creates a Compute Instance with the provided metadata."""

COMPUTE_URL_BASE = 'https://www.googleapis.com/compute/v1/'


def GlobalComputeUrl(project, collection, name):
    """Generate global compute URL."""
    return ''.join([COMPUTE_URL_BASE, 'projects/', project, '/global/', collection, '/', name])


def ZonalComputeUrl(project, zone, collection, name):
    """Generate zone compute URL."""
    return ''.join([COMPUTE_URL_BASE, 'projects/', project, '/zones/', zone, '/', collection, '/', name])


def RegionalComputeUrl(project, region, collection, name):
    """Generate regional compute URL."""
    return ''.join([COMPUTE_URL_BASE, 'projects/', project, '/regions/', region, '/', collection, '/', name])


def GenerateConfig(context):
    """Generate configuration."""

    # Get/generate variables from context
    zone = context.properties['zone']
    project = context.env['project']
    instance_name = context.properties['instanceName']
    instance_type = ZonalComputeUrl(
        project, zone, 'machineTypes', context.properties['instanceType'])
    region = context.properties['zone'][:context.properties['zone'].rfind('-')]
    windows_image_project = context.properties['windowsImageProject']
    windows_image = GlobalComputeUrl(
        windows_image_project, 'images', context.properties['windowsImage'])
    networkTag = str(context.properties.get('networkTag', ''))
    network_tags = {"items": str(context.properties.get('networkTag', '')).split(
        ',') if len(str(context.properties.get('networkTag', ''))) else []}
    service_account = str(context.properties.get(
        'serviceAccount', context.env['project_number'] + '-compute@developer.gserviceaccount.com'))
    primary_startup = """if(![System.IO.File]::Exists('C:\Program Files\Google\Compute Engine\metadata_scripts\createRobotUser')){{
    $UserName= "{vm_username}"
    $Password= "{vm_password}"
    $Computer = [ADSI]'WinNT://$Env:COMPUTERNAME,Computer'
    $User = $Computer.Create('User', $UserName)
    $User.SetPassword('$Password')
    $User.SetInfo()
    $User.FullName = "{vm_username}"
    $User.SetInfo()
    $User.Put('Description', 'UiPath Robot Admin Account')
    $User.SetInfo()
    $User.UserFlags = 65536
    $User.SetInfo()
    $Group = [ADSI]('WinNT://$Env:COMPUTERNAME/Remote Desktop Users,Group')
    $Group.add('WinNT://$Env:COMPUTERNAME/$UserName')
    $admin = [ADSI]('WinNT://./administrator, user')
    $admin.SetPassword("{vm_password}")
    New-Item 'C:\Program Files\Google\Compute Engine\metadata_scripts\createRobotUser' -type file
    }}
    if(![System.IO.File]::Exists('C:\Program Files\Google\Compute Engine\metadata_scripts\installRobot')){{
    Set-ExecutionPolicy Unrestricted -force
    Invoke-WebRequest https://raw.githubusercontent.com/hteo1337/UiRobot/master/Setup/Install-UiRobot.ps1 -OutFile 'C:\Program Files\Google\Compute Engine\metadata_scripts\Install-UiRobot.ps1'
    powershell.exe -ExecutionPolicy Bypass -File 'C:\Program Files\Google\Compute Engine\metadata_scripts\Install-UiRobot.ps1'  -orchestratorUrl '{orchestrator_url}' -Tennant '{orchestrator_tennant}' -orchAdmin '{orchestrator_admin}' -orchPassword '{orchestrator_adminpw}' -adminUsername '{vm_username}' -machinePassword '{vm_password}' -RobotType '{robot_type}'
    New-Item 'C:\Program Files\Google\Compute Engine\metadata_scripts\installRobot' -type file
    powershell.exe Remove-Item -Path  'C:\Program Files\Google\Compute Engine\metadata_scripts\Install-UiRobot.ps1' -Force
    #powershell.exe Start-Sleep -Seconds 10 ; Restart-Computer -Force
    }}"""
    primary_startup_script = primary_startup.format(vm_username=context.properties['vm_username'], vm_password=context.properties['vm_password'], orchestrator_url=context.properties['orchestrator_url'], orchestrator_tennant=context.properties[
                                                    'orchestrator_tennant'], orchestrator_admin=context.properties['orchestrator_admin'], orchestrator_adminpw=context.properties['orchestrator_adminpw'], robot_type=context.properties['robot_type'])
    # Get deployment template specific variables from context
    #robot_hdd_size = context.properties['storageSize']

    # Subnetwork: with SharedVPC support
 #   if "/" in context.properties['subnetwork']:
  #      sharedvpc = context.properties['subnetwork'].split("/")
 #       subnetwork = RegionalComputeUrl(
 #           sharedvpc[0], region, 'subnetworks', sharedvpc[1])
 #   else:
 #       subnetwork = RegionalComputeUrl(
#            project, region, 'subnetworks', context.properties['subnetwork'])
    # Network
    network = RegionalComputeUrl(
        project, region, 'networks', context.properties['network'])
    subnetwork = RegionalComputeUrl(
        project, region, 'subnetworks', context.properties['subnetwork'])
    # Public IP

    if str(context.properties['publicIP']) == "False":
        networking = []
    else:
        networking = [{
            'name': 'external-nat',
            'type': 'ONE_TO_ONE_NAT'
        }]

    # compile complete json
    ui_robot = []
    disks = []

    # /
    disks.append({'deviceName': 'boot',
                  'type': 'PERSISTENT',
                  'boot': True,
                  'autoDelete': True,
                  'initializeParams': {
                      'diskName': instance_name + '-boot',
                      'sourceImage': windows_image,
                      'diskSizeGb': '64'
                  }
                  })

    # if robot_hdd_size > 0:
    #     ui_robot.append({
    #         'name': instance_name + 'r001',
    #         'type': 'compute.v1.disk',
    #         'properties': {
    #                 'zone': zone,
    #                 'sizeGb': robot_hdd_size,
    #                 'type': ZonalComputeUrl(project, zone, 'diskTypes', 'pd-standard')
    #         }
    #     })
    #     disks.append({'deviceName': instance_name + 'r002',
    #                   'type': 'PERSISTENT',
    #                   'source': ''.join(['$(ref.', instance_name, '.selfLink)']),
    #                   'autoDelete': True
    #                   })

    # VM instance
    ui_robot.append({
        'name': instance_name,
        'type': 'compute.v1.instance',
        'properties': {
                'zone': zone,
                'minCpuPlatform': 'Automatic',
                'machineType': instance_type,
                'metadata': {
                    'items': [{
                        'key': 'windows-startup-script-ps1',
                        'value': primary_startup_script
                    }]
                },
            'canIpForward': True,
            'serviceAccounts': [{
                'email': service_account,
                'scopes': [
                    'https://www.googleapis.com/auth/compute',
                    'https://www.googleapis.com/auth/servicecontrol',
                    'https://www.googleapis.com/auth/service.management.readonly',
                    'https://www.googleapis.com/auth/logging.write',
                    'https://www.googleapis.com/auth/monitoring.write',
                    'https://www.googleapis.com/auth/trace.append',
                    'https://www.googleapis.com/auth/devstorage.read_write'
                ]
            }],
            'networkInterfaces': [{
                'network': network,
                'accessConfigs': networking,
                'subnetwork': subnetwork
            }],
            "tags": network_tags,
            'disks': disks
        }
    })

    return {'resources': ui_robot}
