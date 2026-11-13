"""Install gateway client configuration in the bastion namespace."""
import kube

kube.write('lab-api-key', kube.data(kube.read('lab-api-key', ns='gateway')))
kube.write('lab-ca', kube.data(kube.read('lab-ca', ns='gateway', kind='configmaps')))
print('Shared admin workspace API credentials and public CA are ready.')
