"""Copy this model's published IAM credentials into its own namespace."""
import os
import kube

credentials = kube.data(kube.read('s3-' + os.environ['MODEL_NAME'], ns='rustfs'))
for role in ('reader', 'writer'):
    annotations = {'serving.kserve.io/s3-endpoint': 'rustfs-svc.rustfs.svc.cluster.local:9000',
                   'serving.kserve.io/s3-usehttps': '0', 'serving.kserve.io/s3-region': 'us-east-1',
                   'serving.kserve.io/s3-usevirtualbucket': 'false'} if role == 'reader' else {}
    kube.write('model-' + role, {'AWS_ACCESS_KEY_ID': credentials[role + '-access'],
                                 'AWS_SECRET_ACCESS_KEY': credentials[role + '-secret']}, annotations=annotations)
print('Model-local S3 credentials are ready.')
