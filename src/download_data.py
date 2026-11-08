"""Download only events.csv from the publisher; raw data stay outside Git."""
from pathlib import Path
import urllib.request,zipfile,hashlib,shutil

root=Path(__file__).resolve().parents[1]/'.local-data'
root.mkdir(exist_ok=True)
archive=root/'events.zip'
urllib.request.urlretrieve('https://www.kaggle.com/api/v1/datasets/download/retailrocket/ecommerce-dataset/events.csv',archive)
with zipfile.ZipFile(archive) as z:
    name=next(n for n in z.namelist() if n=='events.csv' or n.endswith('/events.csv'))
    with z.open(name) as a,(root/'events.csv').open('wb') as b:shutil.copyfileobj(a,b)
digest=hashlib.sha256((root/'events.csv').read_bytes()).hexdigest()
if digest!='3745aa83238b1e6d44d8fda209807899f420084398f94ddf745f3cbcfecbf9e7':
    raise ValueError('Downloaded version changed. Review source before re-running the frozen report.')
print('Downloaded publisher events.csv; SHA256 verified. Dataset license: CC BY-NC-SA 4.0.')
