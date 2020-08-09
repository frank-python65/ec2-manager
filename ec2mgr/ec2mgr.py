import boto3
import botocore
import click

session = boto3.Session(profile_name='ec2mgr')
ec2 = session.resource('ec2')

def filter_instances(project):
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



@click.group()
def cli():
    """ec2mgr manages EC2 instances and their volumes and snapshot"""

### insatnces functions
@cli.group('instances')
def instances():
    """Commands for managing instances"""

@instances.command('list')
@click.option('--department', default=None,
    help="Only instances for project (tag department:<name>)")
@click.option('--project', default=None,
    help="Only instances for project (tag project:<name>)")

def list_insatnces(department, project):
    "List EC2 instances"
    click.echo('Department: %s!' % department)
    click.echo('Project: %s!' % project)

    instances = filter_instances(project)

    for i in instances:
        tags = {t['Key'] : t['Value'] for t in (i.tags or []) }
        print(','.join((
        i.id,
        tags.get('Project', '<no project>'),
        i.instance_type,
        i.placement['AvailabilityZone'],
        i.state['Name'],
        i.public_dns_name
        )))
    return

@instances.command('stop')
@click.option('--project', default=None,
    help="Only instances for project (tag project:<name>)")

def stop_insatnces(project):
    "Stop EC2 instances"

    instances = filter_instances(project)

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
@click.option('--project', default=None,
    help="Only instances for project (tag project:<name>)")

def start_insatnces(project):
    "Start EC2 instances"

    instances = filter_instances(project)

    for i in instances:
        print ("starting {0} - {1}...".format(project,i.id))
        try:
            i.start()
        except botocore.exceptions.ClientError as e:
            print ("Cloud not start {0} . Error:".format(i.id) + str(e))
            continue

    return

@instances.command('snapshot')
@click.option('--project', default=None,
    help="Only instances for project (tag project:<name>)")

def create_snapshots(project):
    "Create snapshot for volumes of a gourp of instancs"

    instances = filter_instances(project)

    for i in instances:
        print ("stopping {0} for volume snapshots".format(i.id))
        i.stop()
        i.wait_until_stopped()

        for v in i.volumes.all():
            if has_pending_snapshot(v):
                print(" Skipping {0}, snapshot already in progress".format(v.id))
                continue
            print ("Creating snapshot of {0} of {1}".format(v.id, i.id))
            v.create_snapshot(Description="Created by Snapshotalyzer")
        print ("starting {0} after volume snapshots".format(i.id))
        i.start()
        i.wait_until_running()
    return

### volumes functions
@cli.group('volumes')
def volumes():
    """Commands for managing volumes"""

@volumes.command('list')
@click.option('--project', default=None,
    help="Only instances for project (tag project:<name>)")

def list_volumes(project):
    "List EC2 volumes"

    instances = filter_instances(project)

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
@click.option('--project', default=None,
    help="Only instances for project (tag project:<name>)")
@click.option('--all', 'list_all', default=False, is_flag=True,
    help="List all snapshots for each volume, not just most recent one")

def list_snapshots(project, list_all):
    "List EC2 snapshots"

    instances = filter_instances(project)

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
