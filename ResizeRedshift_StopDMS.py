import boto3
import os
import time

clientdms = boto3.client('dms', region_name='ap-northeast-1')
clientredshift = boto3.client('redshift', region_name='ap-northeast-1')

def stoptask():
    task = clientdms.describe_replication_tasks(
        Filters=[
            {
                'Name': 'endpoint-arn',
                'Values': [os.environ['redshift_arn']]
            }
        ]
    )
    for dmstask in task['ReplicationTasks']:
        if dmstask['Status'] == 'running':
            if dmstask['MigrationType'] == 'full-load-and-cdc' or dmstask['MigrationType'] == 'cdc':
                response = clientdms.stop_replication_task(
                    ReplicationTaskArn=os.environ['dmstask_arn']
                )
    return {'Action':'status','ExpectStatus':'stopped'}
                
def starttask():
    task = clientdms.describe_replication_tasks(
        Filters=[
            {
                'Name': 'endpoint-arn',
                'Values': [os.environ['redshift_arn']]
            }
        ]
    )
    for dmstask in task['ReplicationTasks']:
        if dmstask['Status'] == 'stopped':
            if dmstask['MigrationType'] == 'full-load-and-cdc' or dmstask['MigrationType'] == 'cdc':
                response = clientdms.start_replication_task(
                    ReplicationTaskArn=os.environ['dmstask_arn'],
                    StartReplicationTaskType='resume-processing'
                )
    return {'Action':'status','ExpectStatus':'running'}
    
def checktaskstatus(status):
    """
    check if all tasks of redshift reach the specified status
    acceptable input is stopped or running
    """
    task = clientdms.describe_replication_tasks(
        Filters=[
            {
                'Name': 'endpoint-arn',
                'Values': [os.environ['redshift_arn']]
            }
        ]
    )
    for dmstask in task['ReplicationTasks']:
        if dmstask['MigrationType'] == 'full-load-and-cdc' or dmstask['MigrationType'] == 'cdc':
            if dmstask['Status'] != status:
                return {'Action':'status','Finished':'False','ExpectStatus':status}
    return {'Action':'snapshot','Finished':'True'}
    
def resizeredshift():
    """
    double redshift node size until max node size supported by current node type
    this function will not upgrade node type when max node size is reached
    this function will not resize the cluster if it already reach the max node size 
    """
    redshift = clientredshift.describe_clusters(
        ClusterIdentifier=os.environ['redshift_name'],
    )
    node_type = redshift['Clusters'][0]['NodeType']
    if node_type == 'ds2.xlarge' or node_type == 'dc2.large' or node_type == 'dc1.large':
        max_node_num = 32
    elif node_type == 'ds2.8xlarge' or node_type == 'dc2.8xlarge' or node_type == 'dc1.8xlarge':
        max_node_num = 128
    node_num = redshift['Clusters'][0]['NumberOfNodes']*2
    if node_num > max_node_num:
        node_num = max_node_num
    if redshift['Clusters'][0]['NumberOfNodes'] < max_node_num:
        clientredshift.modify_cluster(
            ClusterIdentifier=os.environ['redshift_name'],
            ClusterType='multi-node',
            NodeType=node_type,
            NumberOfNodes=node_num
        )
        return {'Action':'resizestatus','ExpectStatus':'available','maxnode':'False'}
    elif redshift['Clusters'][0]['NumberOfNodes'] == max_node_num:
        return {'Action':'startdms','maxnode':'True'}
   
def checkredshiftstatus(status):
    """
    check redshift status (resizing,available)
    """
    redshift = clientredshift.describe_clusters(
        ClusterIdentifier=os.environ['redshift_name'],
    )
    if redshift['Clusters'][0]['ClusterStatus'] == status:
        return {'Action':'startdms','Finished':'True'}
    else:
        return {'Action':'resizestatus','ExpectStatus':status,'Finished':'False'}
    
def snapshotredshift():
    SnapshotId = 'RedshiftResize-'+time.strftime('%Y-%m-%d-%H-%M-%S',time.localtime(time.time()))
    response = clientredshift.create_cluster_snapshot(
        SnapshotIdentifier=SnapshotId,
        ClusterIdentifier=os.environ['redshift_name']
    )
    return {'Action':'resize'}

def lambda_handler(event, context):
    if event['Action'] == 'stopdms':
        Status = stoptask()
    elif event['Action'] == 'status':
        Status = checktaskstatus(event['ExpectStatus'])
    elif event['Action'] == 'snapshot':
        Status = snapshotredshift()
    elif event['Action'] == 'resize':
        Status = resizeredshift()
    elif event['Action'] == 'resizestatus':
        Status = checkredshiftstatus(event['ExpectStatus'])
    elif event['Action'] == 'startdms':
        Status = starttask()        
    return Status
