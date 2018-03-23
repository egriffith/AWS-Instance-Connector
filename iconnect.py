#! /usr/bin/env python3

import argparse
import sys
import time
import os

try:
    import boto3
    import botocore
except ImportError:
    print("The boto3 SDK for python3 is not available. Please install it.")
    sys.exit(1)

def buildArgParser(argv):
    parser = argparse.ArgumentParser(description="Update a Route53 DNS record based upon current public IP.")

    parser.add_argument("instanceId",
                        help="Specify the instance id to connect to.")

    parser.add_argument("--region", "-r", 
                        dest="region",
                        help="Specify the region the instance resides in. Otherwise will check every region.")

    parser.add_argument("--profile", "-p", 
                        dest="credProfile", 
                        help="Specify the profile to use from your AWS credentials file")

    parser.add_argument("--user", "-u",
                        dest="username", 
                        default="ec2-user", 
                        help="Specify the username to connect with. Defaults to ec2-user.")

    parser.add_argument("--private",
                        dest="privateNetFlag",
                        action='store_true',
                        help="Specify whether to query for private IP / DNS information.")

    return parser.parse_args()

def findInstanceRegion(instanceId):
    regionList = botoSession.get_available_regions("ec2")
    foundIt = False

    for region in regionList:
        print("Checking: ", region, flush=True)
        client = botoSession.client("ec2", region_name=region)
        try:
            client.describe_instances(InstanceIds=[instanceId])
        except client.exceptions.ClientError:
            continue
        foundIt = True
        break

    if foundIt == False:
        print("Unable to find the instance id you provided in any region using the credentials specified. Bailing out.")
        sys.exit(1)

    return region

def describeInstance(instanceId):
    global response
    try:
            response = ec2Client.describe_instances(InstanceIds=[instanceId])
    except ec2Client.exceptions.ClientError:
        print("Ran into an error while getting the instance's metadata. Safest thing we can do here is bail out.")
        sys.exit(1)
    
def getInstanceState():
    return response['Reservations'][0]['Instances'][0]['State']['Name']

def parseInstanceState(state, instanceId):    
    if state == "stopped":
        print("Instance is stopped. Starting it up...",flush=True)
        startInstance(instanceId)
    elif state == "shutting-down":
        print("Instance is shutting down. Exiting.")
        sys.exit(1)
    elif state == "stopping":
        print("Instance is stopping. Exiting.")
        sys.exit(1)
    elif state == "terminated":
        print("Instance's state is terminated.")
        sys.exit(1)
    elif state == "pending":
        print("Instance is still starting up. Waiting 10 seconds to give it time to settle.",flush=True)
        time.sleep(5)
        describeInstance(instanceId)


def startInstance(instanceId):
    ec2Client.start_instances(
        InstanceIds=[instanceId,]
    )
    print("Had to start the instance. Waiting 30 seconds to give the instance time to come up.",flush=True)
    time.sleep(30)
    describeInstance(instanceId)
    return 0

def getInstanceDNS(privateNetFlag):
    if privateNetFlag == True:
        return response['Reservations'][0]['Instances'][0]['PrivateDnsName']
    else:
        return response['Reservations'][0]['Instances'][0]['PublicDnsName']

def getInstanceKey():
    return response['Reservations'][0]['Instances'][0]['KeyName'] + ".pem"

def connectToInstance(sshKeyName, username, DNS):
    command = "ssh -i ~/.ssh/" + sshKeyName + " " + username + "@" + DNS
    print(command)
    os.system(command)

def main(argv):
    global ec2Client
    global botoSession

    arglist = buildArgParser(argv)

    botoSession = boto3.Session(profile_name=arglist.credProfile)

    if arglist.region == None:
        ec2Region = findInstanceRegion(arglist.instanceId)
    else:
        ec2Region = arglist.region

    ec2Client = botoSession.client("ec2", region_name=ec2Region)
    
    describeInstance(arglist.instanceId)

    instanceState = getInstanceState()
    parseInstanceState(instanceState, arglist.instanceId)

    keyName = getInstanceKey()
    DNS = getInstanceDNS(arglist.privateNetFlag)
    connectToInstance(keyName,arglist.username,DNS)


if __name__ == "__main__":
   main(sys.argv[1:])