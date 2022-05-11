from pathlib import Path

from absl import app, flags
from webdav3.client import Client

FLAGS = flags.FLAGS
flags.DEFINE_string("remote_path", None, "Remote directory where the pdfs are stored")
flags.DEFINE_string("local_path", None, "Local directory where the pdfs will be downloaded")
flags.DEFINE_string("wd_hostname", None, "WEBDAV hostname")
flags.DEFINE_string("wd_login", None, "WEBDAV loginh")
flags.DEFINE_string("wd_password", None, "WEBDAV password")
                                                       
# Required flag.
flags.mark_flag_as_required("remote_path")
flags.mark_flag_as_required("local_path")
flags.mark_flag_as_required("wd_hostname")
flags.mark_flag_as_required("wd_login")
flags.mark_flag_as_required("wd_password")



def main(argv):
    del argv 

    REMOTE_PATH = Path(FLAGS.remote_path)
    LOCAL_PATH = Path(FLAGS.local_path)

    options = {
    'webdav_hostname': FLAGS.wd_hostname,
    'webdav_login':    FLAGS.wd_login,
    'webdav_password': FLAGS.wd_password
    }

    client = Client(options)

    assert client.check(str(REMOTE_PATH))

    remote_files = []
    for year in client.list(str(REMOTE_PATH))[1:]:
        remote_files += [REMOTE_PATH / year / file for file in client.list(str(REMOTE_PATH / year))[1:]]

    if not LOCAL_PATH.exists():
        LOCAL_PATH.mkdir(parents=True)

    local_files = list(LOCAL_PATH.glob('*/*.pdf'))

    missing_files = {str(i).replace(str(REMOTE_PATH) + '/','') for i in remote_files} - {str(i).replace(str(LOCAL_PATH) + '/','') for i in local_files}

    for file in missing_files:
        (LOCAL_PATH / file).parent.mkdir(exist_ok=True, parents=True)
        client.download_sync(str(REMOTE_PATH / file), str(LOCAL_PATH / file))

if __name__ == '__main__':
    app.run(main)
