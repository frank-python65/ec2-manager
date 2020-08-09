import boto3
import botocore
import click

# specify the AWS account used for access AWS resources
session = boto3.Session(profile_name='ec2mgr')
ec2 = session.resource('ec2')

def filter_instancesold(project):
    instance = []

    if project:
        filters = [{'Name':'tag:Project', 'Values':[project]}]
        instances = ec2.instances.filter(Filters=filters)
    else:
        instances = ec2.instances.all()
    return instances

def has_pending_snapshot(volume):
    snapshots = list(volume.snapshots.all())
    return snapshots and snapshots[0].state == 'pending'

def filter_instances(department, project):
    instance = []
    click.echo('Instance Filter-Department: %s!' % department)
    click.echo('Instance Filter-Project: %s!' % project)

    if (department) and (project):
        #click.echo("Branch: (department) and (project)")
        filters = [{'Name':'tag:Department', 'Values':[department]}, 
                    {'Name':'tag:Project', 'Values':[project]}]
        instances = ec2.instances.filter(Filters=filters)
    elif (department) and (not project):
        #click.echo("Branch: (department) and (not project)")
        filters = [{'Name':'tag:Department', 'Values':[department]}]
        instances = ec2.instances.filter(Filters=filters)
    elif (not department) and (project):
        #click.echo("Branch: (not department) and (project)")
        filters = [{'Name':'tag:Project', 'Values':[project]}]
        instances = ec2.instances.filter(Filters=filters)
    else:
        #click.echo("Branch: (not department) and (not project)")        
        instances = ec2.instances.all()
    return instances

def has_pending_snapshot(volume):
    snapshots = list(volume.snapshots.all())
    return snapshots and snapshots[0].state == 'pending'



@click.group()
def cli():
    """ec2mgr manages EC2 instances and their volumes and snapshot based on Department and Project"""

### insatnces functions
@cli.group('instances')
def instances():
    """Commands for managing instances"""

@instances.command('list')
@click.option('--department', default=None,
    help="Only instances for department (tag department:<name>)")
@click.option('--project', default=None,
    help="Only instances for project (tag project:<name>)")

def list_insatnces(department, project):
    "List EC2 instances"
    click.echo('Department: %s!' % department)
    click.echo('Project: %s!' % project)

    instances = filter_instances(department, project)

    for i in instances:
        tags = {t['Key'] : t['Value'] for t in (i.tags or []) }
        print(','.join((
        i.id,
        tags.get('Department', '<no department>'),
        tags.get('Project', '<no project>'),
        i.instance_type,
        i.placement['AvailabilityZone'],
        i.state['Name'],
        i.public_dns_name
        )))
    return

@instances.command('stop')
@click.option('--department', default=None,
    help="Only instances for department (tag department:<name>)")
@click.option('--project', default=None,
    help="Only instances for project (tag project:<name>)")

def stop_insatnces(department, project):
    "Stop EC2 instances"

    instances = filter_instances(department, project)

    for i in instances:
        print ("stopping {0} - {1}...".format(project,i.id))
        # add error handling
        try:
            i.stop()
        except botocore.exceptions.ClientError as e:
            print ("Cloud not stop {0} . Error:".format(i.id) + str(e))
            continue
    return

@instances.command('start')
@click.option('--department', default=None,
    help="Only instances for department (tag department:<name>)")
@click.option('--project', default=None,
    help="Only instances for project (tag project:<name>)")

def start_insatnces(department, project):
    "Start EC2 instances"

    instances = filter_instances(department, project)

    for i in instances:
        print ("starting {0} - {1}...".format(project,i.id))
        try:
            i.start()
        except botocore.exceptions.ClientError as e:
            print ("Cloud not start {0} . Error:".format(i.id) + str(e))
            continue

    return

@instances.command('snapshot')
@click.option('--consistency', default=None,
    help="Use 'Force' will get application consistency snapshot by stop-snapshot-start runing instances")
@click.option('--department', default=None,
    help="Only instances for department (tag department:<name>)")
@click.option('--project', default=None,
    help="Only instances for project (tag project:<name>)")

def create_snapshots(consistency, department, project):
    "Create snapshot for volumes of a gourp of instancs"

    instances = filter_instances(department, project)

    for i in instances:
        i_status=i.state['Name']
        #print(i.state)
        #print ("Tags of {0} - {1}".format(i.id, i.tags))
        #i_department = ""
        #i_project = ""
        #for tags in i.tags:
        #    if tags["Key"] == 'Department':
        #        i_department = tags["Value"]
        #    if tags["Key"] == 'Project':
        #        i_project = tags["Value"]
        #click.echo ("Department: %s" % i_department)
        #click.echo ("Project: %s" % i_project)

        #tag_department=i.tags.get('Department', '<no department>')
        #tag_project=tags.get('Project', '<no project>')
        #print ("insatnce status: ", tag_department, tag_project, i_status)

        if ((i_status == "running") and (consistency == "Force")):
            print ("stopping {0} for app-consitency volume snapshots".format(i.id))
            i.stop()
            i.wait_until_stopped()
        
        for v in i.volumes.all():
            if has_pending_snapshot(v):
                print(" Skipping {0}, snapshot already in progress".format(v.id))
                continue
            print ("Creating snapshot of {0} of {1} ".format(v.id, i.id))
            v.create_snapshot(Description='ec2mgr Snapshot of volume ({})'.format(v.id), 
                TagSpecifications=[
                    {
                    'ResourceType': 'snapshot',
                    'Tags' : v.tags,
                    },
                ],
            )

        if ((i_status == "running") and (consistency == "Force")):
            print ("restarting {0} after app-consitency volume snapshots".format(i.id))
            i.start()
            i.wait_until_running()
    return

### volumes functions
@cli.group('volumes')
def volumes():
    """Commands for managing volumes"""

@volumes.command('list')
@click.option('--department', default=None,
    help="Only instances for department (tag department:<name>)")
@click.option('--project', default=None,
    help="Only instances for project (tag project:<name>)")

def list_volumes(department, project):
    "List EC2 volumes"

    instances = filter_instances(department, project)

    for i in instances:
        for v in i.volumes.all():
             print(",".join((
             v.id,
             i.id,
             v.state,
             str(v.size)+"GB",
             v.encrypted and "Encrypted" or "Not Encrypted"
             )))
    return

### snapshots functions
@cli.group('snapshots')
def snapshots():
    """Commands for managing snapshots"""

@snapshots.command('list')
@click.option('--department', default=None,
    help="Only instances for department (tag department:<name>)")
@click.option('--project', default=None,
    help="Only instances for project (tag project:<name>)")
@click.option('--all', 'list_all', default=False, is_flag=True,
    help="List all snapshots for each volume, not just most recent one")

def list_snapshots(department, project, list_all):
    "List EC2 snapshots"

    instances = filter_instances(department, project)

    for i in instances:
        for v in i.volumes.all():
            for s in v.snapshots.all():
                 print(",".join((
                 s.id,
                 v.id,
                 i.id,
                 s.state,
                 s.progress,
                 s.start_time.strftime("%c")
                 )))
                 if s.state == 'completed' and not list_all: break
    return

@cli.group('snapshots')
def snapshots():
    """Commands for managing snapshots"""

@snapshots.command('delete')
@click.option('--department', default=None,
    help="Only instances for department (tag department:<name>)")
@click.option('--project', default=None,
    help="Only instances for project (tag project:<name>)")
@click.option('--older', 'list_all', default=False, is_flag=True,
    help="List all snapshots for each volume, not just most recent one")

def list_snapshots(department, project, list_all):
    "List EC2 snapshots"

    instances = filter_instances(department, project)

    for i in instances:
        for v in i.volumes.all():
            for s in v.snapshots.all():
                 print(",".join((
                 s.id,
                 v.id,
                 i.id,
                 s.state,
                 s.progress,
                 s.start_time.strftime("%c")
                 )))
                 if s.state == 'completed' and not list_all: break
    return

if __name__ == '__main__':
    cli()
