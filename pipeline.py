import time
import os
import os.path
import shutil
import glob

from seesaw.project import *
from seesaw.config import *
from seesaw.item import *
from seesaw.task import *
from seesaw.pipeline import *
from seesaw.externalprocess import *
from seesaw.tracker import *

DATA_DIR = "data"
USER_AGENT = "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/533.20.25 (KHTML, like Gecko) Version/5.0.4 Safari/533.20.27"
VERSION = "20120903.01"

class PrepareDirectories(SimpleTask):
  def __init__(self):
    SimpleTask.__init__(self, "PrepareDirectories")

  def process(self, item):
    item_name = item["item_name"]
    dirname = "/".join(( DATA_DIR, item_name ))

    if os.path.isdir(dirname):
      shutil.rmtree(dirname)

    os.makedirs(dirname + "/files")

    item["item_dir"] = dirname
    item["data_dir"] = DATA_DIR
    item["warc_file_base"] = "boards.cityofheroes.com-threads-range-%s-%s" % (item_name, time.strftime("%Y%m%d-%H%M%S"))

class MoveFiles(SimpleTask):
  def __init__(self):
    SimpleTask.__init__(self, "MoveFiles")

  def process(self, item):
    os.rename("%(item_dir)s/%(warc_file_base)s.warc.gz" % item,
              "%(data_dir)s/%(warc_file_base)s.warc.gz" % item)

    shutil.rmtree("%(item_dir)s" % item)

class DeleteFiles(SimpleTask):
  def __init__(self):
    SimpleTask.__init__(self, "DeleteFiles")

  def process(self, item):
    os.unlink("%(data_dir)s/%(warc_file_base)s.warc.gz" % item)

def calculate_item_id(item):
  thread_htmls = glob.glob("%(item_dir)s/files/boards.cityofheroes.com/showthread.php*" % item)
  n = len(thread_htmls)
  if n == 0:
    return "null"
  else:
    return thread_htmls[0] + "-" + thread_htmls[n-1]


project = Project(
  title = "City of Heroes Forums",
  project_html = """
    <img class="project-logo" alt="City of Heroes logo" src="http://archiveteam.org/images/thumb/2/28/Cityofheroes-logo.png/120px-Cityofheroes-logo.png" />
    <h2>City of Heroes Forums <span class="links"><a href="http://boards.cityofheroes.com/">Website</a> &middot; <a href="http://tracker.archiveteam.org/cityofheroes/">Leaderboard</a></span></h2>
    <p>The City of Heroes forums may disappear!</p>
  """,
  utc_deadline = datetime.datetime(2012,11,30, 23,59,0)
)

pipeline = Pipeline(
  GetItemFromTracker("http://tracker.archiveteam.org/cityofheroes", downloader, VERSION),
  PrepareDirectories(),
  WgetDownload([ "./wget-lua",
      "-U", USER_AGENT,
      "-nv",
      "-o", ItemInterpolation("%(item_dir)s/wget.log"),
      "--directory-prefix", ItemInterpolation("%(item_dir)s/files"),
      "--keep-session-cookies",
      "--save-cookies", ItemInterpolation("%(item_dir)s/files/cookies.txt"),
      "--force-directories",
      "--adjust-extension",
      "-e", "robots=off",
      "--page-requisites", "--span-hosts",
      "--lua-script", "vbulletin.lua",
      "--warc-file", ItemInterpolation("%(item_dir)s/%(warc_file_base)s"),
      "--warc-header", "operator: Archive Team",
      "--warc-header", "cityofheroes-dld-script-version: " + VERSION,
      "--warc-header", ItemInterpolation("cityofheroes-threads-range: %(item_name)s"),
      ItemInterpolation("http://boards.cityofheroes.com/external.php?type=RSS2"), # initializes the cookies
      ItemInterpolation("http://boards.cityofheroes.com/showthread.php?t=%(item_name)s0"),
      ItemInterpolation("http://boards.cityofheroes.com/showthread.php?t=%(item_name)s1"),
      ItemInterpolation("http://boards.cityofheroes.com/showthread.php?t=%(item_name)s2"),
      ItemInterpolation("http://boards.cityofheroes.com/showthread.php?t=%(item_name)s3"),
      ItemInterpolation("http://boards.cityofheroes.com/showthread.php?t=%(item_name)s4"),
      ItemInterpolation("http://boards.cityofheroes.com/showthread.php?t=%(item_name)s5"),
      ItemInterpolation("http://boards.cityofheroes.com/showthread.php?t=%(item_name)s6"),
      ItemInterpolation("http://boards.cityofheroes.com/showthread.php?t=%(item_name)s7"),
      ItemInterpolation("http://boards.cityofheroes.com/showthread.php?t=%(item_name)s8"),
      ItemInterpolation("http://boards.cityofheroes.com/showthread.php?t=%(item_name)s9")
    ],
    max_tries = 2,
    accept_on_exit_code = [ 0, 4, 6, 8 ],
  ),
  PrepareStatsForTracker(
    defaults = { "downloader": downloader, "version": VERSION },
    file_groups = {
      "data": [ ItemInterpolation("%(item_dir)s/%(warc_file_base)s.warc.gz") ]
    },
    id_function = calculate_item_id
  ),
  MoveFiles(),
  LimitConcurrent(1,
    RsyncUpload(
      target = ConfigInterpolation("fos.textfiles.com::cinch/cityofheroes/%s/", downloader),
      target_source_path = ItemInterpolation("%(data_dir)s/"),
      files = [
        ItemInterpolation("%(warc_file_base)s.warc.gz")
      ],
      extra_args = [
        "--partial-dir", ".rsync-tmp"
      ]
    ),
  ),
  SendDoneToTracker(
    tracker_url = "http://tracker.archiveteam.org/cityofheroes",
    stats = ItemValue("stats")
  ),
  DeleteFiles()
)

