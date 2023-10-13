#!/usr/bin/env python3
import argparse
import configparser
import os
import os.path
import sys
from pathlib import Path
from typing import Optional

try:
    from atlassian import Jira
    from ruamel.yaml import YAML
    from tqdm import tqdm
except ModuleNotFoundError as e:
    print("Please install the modules from the requirement.txt file first !\n", file=sys.stderr)
    raise e


# https://gist.github.com/yanqd0/c13ed29e29432e3cf3e7c38467f42f51
def download_with_progress_bar(session, url: str, fname: str, chunk_size=1024):
    resp = session.get(url, stream=True, allow_redirects=True)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    if os.path.exists(fname):
        fstats = os.stat(fname)
        if fstats.st_size == total:
            print("File {} already downloaded".format(fname))
            return
    with open(fname, "wb") as file, tqdm(
        desc=fname,
        total=total,
        unit="iB",
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in resp.iter_content(chunk_size=chunk_size):
            size = file.write(data)
            bar.update(size)


class NotDownloaded:
    def __str__(self):
        return "<not downloaded>"

    def __repr__(self):
        return "NOT_DOWNLOADED"

    def to_text(self):
        return "<not downloaded>"


NOT_DOWNLOADED = NotDownloaded()


def have_data(value):
    return value is not None and value is not NOT_DOWNLOADED


class JiraRestObject:
    def __init__(self, data):
        self._data = data

    @property
    def self_url(self):
        return self.get_value("self")

    def get_value(self, key, default=None):
        return self._data.get(key, default)

    def __eq__(self, other):
        return isinstance(other, JiraRestObject) and self.self_url == other.self_url

    def __str__(self):
        return "{}({!r})".format(self.__class__.__name__, self.self_url)

    def create_object_from_value(self, cls, key, default=None):
        value = self.get_value(key, default=None)
        if value is not None:
            return cls(value)
        return default

    @classmethod
    def create_if(cls, data):
        if data is not None:
            return cls(data)
        return None

    @classmethod
    def create_from_dict_and_key(cls, data_dict, key):
        value = data_dict.get(key, None)
        if value is not None:
            return cls(value)
        return None


class JiraIdObject(JiraRestObject):
    def __init__(self, data):
        super().__init__(data)

    @property
    def id(self):
        return self.get_value("id")


class JiraNamedObject(JiraIdObject):
    def __init__(self, data):
        super().__init__(data)

    @property
    def icon_url(self):
        return self.get_value("iconUrl", None)

    @property
    def name(self):
        return self.get_value("name", None)


class JiraProject(JiraIdObject):
    def __init__(self, data):
        super().__init__(data)


class JiraAuthor(JiraRestObject):
    def __init__(self, data):
        super().__init__(data)

    @property
    def account_id(self):
        return self.get_value("accountId")

    @property
    def email_address(self):
        return self.get_value("emailAddress")

    @property
    def avatar_urls(self):
        return self.get_value("avatarUrls")

    @property
    def display_name(self):
        return self.get_value("displayName")

    @property
    def active(self):
        return self.get_value("active")

    @property
    def timezone(self):
        return self.get_value("timeZone")

    @property
    def account_type(self):
        return self.get_value("accountType")

    def to_struct(self):
        return {
            "displayName": self.display_name,
        }

    def to_text(self):
        return self.display_name


class JiraCommentList(JiraRestObject):
    def __init__(self, data):
        super().__init__(data)
        self._comments = [JiraComment(c) for c in self.get_value("comments", [])]

    @property
    def comments(self):
        return self._comments

    @property
    def max_results(self):
        return self.get_value("maxResults")

    @property
    def total(self):
        return self.get_value("total")

    @property
    def start_at(self):
        return self.get_value("startAt")

    def to_struct(self):
        return [c.to_struct() for c in self._comments if c is not None]

    def to_text(self):
        result = "\n".join([c.to_text() for c in self._comments if c is not None])
        return result

    def __len__(self):
        return len(self._comments)


class JiraComment(JiraIdObject):
    def __init__(self, data):
        super().__init__(data)
        self._author_object = self.create_object_from_value(JiraAuthor, "author")

    @property
    def author_object(self):
        return self._author_object

    @property
    def body(self):
        return self.get_value("body")

    @property
    def created(self):
        return self.get_value("created")

    @property
    def updated(self):
        return self.get_value("updated")

    @property
    def jsd_public(self):
        return self.get_value("jsdPublic")

    def to_struct(self):
        result = {"body": self.body, "created": self.created, "updated": self.updated}
        if self.author_object:
            result["author"] = self.author_object.to_struct()
        return result

    def to_text(self):
        if self.author_object:
            author = self.author_object.to_text()
        else:
            author = "<unknown author>"
        author_and_date = "{} {}".format(author, self.created)
        sep = "-" * len(author_and_date)
        return f"{sep}\n{author_and_date}\n{sep}\n{self.body}\n"


class JiraResolution(JiraIdObject):
    def __init__(self, data):
        super().__init__(data)

    @property
    def description(self):
        return self.get_value("description", None)

    @property
    def name(self):
        return self.get_value("name", None)

    def to_struct(self):
        return {
            "type": "JiraResolution",
            "description": self.description,
            "name": self.name,
        }

    def to_text(self):
        return "Resolution: {}".format(self.name)


class JiraStatusCategory(JiraIdObject):
    def __init__(self, data):
        super().__init__(data)

    @property
    def key(self):
        return self.get_value("key", None)

    @property
    def color_name(self):
        return self.get_value("colorName", None)

    @property
    def name(self):
        return self.get_value("name", None)


class JiraStatus(JiraIdObject):
    def __init__(self, data):
        super().__init__(data)
        self._status_category = self.create_object_from_value(JiraStatusCategory, "statusCategory")

    @property
    def key(self):
        return self.get_value("key")

    @property
    def description(self):
        return self.get_value("description", None)

    @property
    def icon_url(self):
        return self.get_value("iconUrl", None)

    @property
    def name(self):
        return self.get_value("name", None)

    @property
    def status_category(self):
        return self._status_category


class JiraPriority(JiraNamedObject):
    def __init__(self, data):
        super().__init__(data)


class JiraIssueType(JiraNamedObject):
    def __init__(self, data):
        super().__init__(data)

    @property
    def description(self):
        return self.get_value("description", None)

    @property
    def subtask(self):
        return self.get_value("subtask", None)

    @property
    def avatar_id(self):
        return self.get_value("avatarId", None)

    @property
    def hierarchy_level(self):
        return self.get_value("hierarchyLevel", None)


class JiraAttachment(JiraIdObject):
    def __init__(self, data):
        super().__init__(data)
        self._author = self.create_object_from_value(JiraAuthor, "author")

    @property
    def author(self):
        return self._author

    @property
    def filename(self):
        return self.get_value("filename", None)

    @property
    def created(self):
        return self.get_value("created", None)

    @property
    def size(self):
        return self.get_value("size", None)

    @property
    def mime_type(self):
        return self.get_value("mimeType", None)

    @property
    def content(self):
        return self.get_value("content", None)

    @property
    def thumbnail(self):
        return self.get_value("thumbnail", None)

    def download(self, session, dest_dir: Optional[str] = None):
        path = os.path.join(dest_dir, self.filename) if dest_dir is not None else self.filename
        download_with_progress_bar(session, self.content, path)


class JiraIssue(JiraIdObject):
    def __init__(self, data):
        super().__init__(data)
        self._fields = self.get_value("fields")
        self._parent_issue = self.create_object_from_field(JiraIssue, "parent")
        self._resolution_object = self.create_object_from_field(JiraResolution, "resolution")
        self._comments = self.create_object_from_field(JiraCommentList, "comment")
        self._status = self.create_object_from_field(JiraStatus, "status")
        self._priority = self.create_object_from_field(JiraPriority, "priority")
        self._reporter = self.create_object_from_field(JiraAuthor, "reporter")
        self._assignee = self.create_object_from_field(JiraAuthor, "assignee")
        self._issuetype = self.create_object_from_field(JiraIssueType, "issuetype")
        self._subtasks = [JiraIssue(c) for c in self.get_field("subtasks", [])]
        self._attachment = [JiraAttachment(c) for c in self.get_field("attachment", [])]

    def create_object_from_field(self, cls, key, default=NOT_DOWNLOADED):
        value = self.get_field(key, default=NOT_DOWNLOADED)
        if value is not NOT_DOWNLOADED and value is not None:
            return cls(value)
        return default

    @property
    def fields(self):
        return self._fields

    @property
    def key(self):
        return self.get_value("key")

    def get_field(self, field_name, default=NOT_DOWNLOADED):
        return self._fields.get(field_name, default)

    @property
    def description(self):
        return self.get_field("description")

    @property
    def summary(self):
        return self.get_field("summary")

    @property
    def labels(self):
        return self.get_field("labels")

    @property
    def statuscategorychangedate(self):
        return self.get_field("statuscategorychangedate")

    @property
    def status(self):
        return self._status

    @property
    def issuetype(self):
        return self._issuetype

    @property
    def priority(self):
        return self._priority

    @property
    def reporter(self):
        return self._reporter

    @property
    def assignee(self):
        return self._assignee

    @property
    def resolution_object(self):
        return self._resolution_object

    @property
    def parent_issue(self):
        return self._parent_issue

    @property
    def created(self):
        return self.get_field("created")

    @property
    def updated(self):
        return self.get_value("updated")

    @property
    def resultiondate(self):
        return self.get_field("resolutiondate")

    @property
    def subtasks(self):
        return self._subtasks

    @property
    def comments(self) -> Optional[JiraCommentList]:
        return self._comments

    @property
    def attachment(self):
        return self._attachment

    def to_struct(self):
        result = {
            "type": "JiraIssue",
            "key": self.key,
            "summary": self.summary,
            "description": self.description,
            "created": self.created,
            "labels": self.labels,
            "updated": self.updated,
            "resolutiondate": self.resultiondate,
        }
        if have_data(self.parent_issue):
            result["parent"] = self.parent_issue.key
        if have_data(self.resolution_object):
            result["resolution"] = self.resolution_object.to_struct()
        if have_data(self.comments):
            result["comments"] = self.comments.to_struct()
        return result

    def to_text(self):
        subtasks = ", ".join((s.key for s in self.subtasks)) if self.subtasks else "none"

        result = """Issue: {key}
Type: {issuetype.name}
Status: {status.name}
Priority: {priority.name}
Reporter: {reporter}
Assignee: {assignee}
Resolution: {resolution}
Subtasks: {subtasks}
Summary: {summary}
Description:

{description}
---
Labels: {labels}
Created: {created}
Updated: {updated}
Comments:

{comments}""".format(
            key=self.key,
            issuetype=self.issuetype,
            status=self.status,
            priority=self.priority,
            reporter=self.reporter.display_name if have_data(self.reporter) else "Unknown",
            assignee=self.assignee.display_name if have_data(self.assignee) else "Unknown",
            resolution=self.resolution_object.name if have_data(self.resolution_object) else "Unresolved",
            subtasks=subtasks,
            summary=self.summary,
            description=self.description,
            labels=", ".join(self.labels),
            created=self.created,
            updated=self.updated,
            comments=self.comments.to_text(),
        )
        return result

    def download_attachment(self, session, dest_dir: Optional[str] = None):
        for a in self.attachment:
            a.download(session, dest_dir)


def jira_get_issues(jira: Jira, jql: str, fields="*all"):
    start = 0
    limit = 200
    total = -1
    while True:
        data = jira.jql(jql, start=start, limit=limit)
        if total == -1:
            total = data.get("total")
        issues = data.get("issues")
        num_issues = len(issues)
        if num_issues > 0:
            for issue_dict in issues:
                yield issue_dict
        if num_issues == 0:
            break
        start = start + num_issues


def main(args):
    if not os.path.isfile(args.config_file):
        print("Error: Configuration file", args.config_file, "not found", file=sys.stderr)
        sys.exit(1)
    cfg_parser = configparser.ConfigParser(interpolation=None)
    cfg_parser.read(args.config_file)
    atlassian_domain = args.atlassian_domain if args.atlassian_domain else cfg_parser.get(configparser.DEFAULTSECT, "domain")
    user = cfg_parser.get(atlassian_domain, "user", fallback=None)
    if user is None:
        print("Error: user is not specified in configuration file", args.config_file, file=sys.stderr)
        sys.exit(1)
    password = cfg_parser.get(atlassian_domain, "api_token", fallback=None)
    if password is None:
        print("Error: api_token is not specified in configuration file", args.config_file, file=sys.stderr)
        sys.exit(1)
    jql = args.jql if args.jql else cfg_parser.get(configparser.DEFAULTSECT, "jql")

    print("Atlassian domain: {}".format(atlassian_domain))
    print("Atlassian user: {}".format(user))
    print("Output issues to the directory: {}".format(args.dest_dir))
    print("Output format: {}".format(args.output_format))
    print("JQL: {}".format(jql))

    os.makedirs(args.dest_dir, exist_ok=True)
    jira = Jira(url="https://" + atlassian_domain, username=user, password=password)

    num_issues = 0
    for issue_dict in jira_get_issues(jira, jql):
        issue = JiraIssue(issue_dict)
        num_issues += 1

        if issue.comments.total != len(issue.comments):
            print("Need to download comments: total = {}, have = {}".format(issue.comments.total, len(issue.comments)))

        browse_url = "https://{}/browse/{}".format(atlassian_domain, issue.key)
        if args.output_format == "yaml":
            yaml_dumper = YAML()
            issue_file_path = os.path.join(args.dest_dir, issue.key + ".yaml")
            print("issue {} -> {}".format(issue.key, issue_file_path))
            with open(issue_file_path, "w") as f:
                issue_struct = issue.to_struct()
                issue_key = issue_struct.get("key")
                if issue_key is not None:
                    issue_struct["browse_url"] = browse_url
                yaml_dumper.dump(issue.to_struct(), f)
        elif args.output_format == "text":
            issue_file_path = os.path.join(args.dest_dir, issue.key + ".txt")
            print("issue {} -> {}".format(issue.key, issue_file_path))
            with open(issue_file_path, "w") as f:
                f.write("Link: " + browse_url + "\n")
                issue_text = issue.to_text()
                f.write(issue_text)
        # Download attachments
        if args.download_attachments:
            issue_dir = Path(args.dest_dir) / issue.key
            issue_dir.mkdir(parents=True, exist_ok=True)
            issue.download_attachment(jira.session, str(issue_dir))

    print("Downloaded {} issues".format(num_issues))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download jira issues", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--atlassian-domain",
        type=str,
        metavar="DOMAIN",
        help="Atlassian domain from which the Jira issues are to be downloaded. "
        "If not specified, value of 'domain' from the DEFAULTS section of the configuration file is used.",
    )
    parser.add_argument(
        "--config-file",
        type=str,
        default="config.ini",
        metavar="FILENAME",
        help="INI configuration file with Atlassian credentials",
    )
    parser.add_argument(
        "--dest-dir",
        type=str,
        default="issues",
        metavar="DIRECTORY",
        help="Output directory where the issues will be saved",
    )
    parser.add_argument(
        "--jql",
        type=str,
        help="JQL query to find issues."
        "If not specified, value of 'jql' from the DEFAULTS section of the configuration file is used.",
    )
    parser.add_argument(
        "-f",
        "--format",
        type=str,
        help="output format",
        choices=["yaml", "text"],
        default="text",
        dest="output_format",
    )
    parser.add_argument(
        "-d",
        "--download-attachments",
        action="store_true",
        help="download and store attachments",
    )
    args = parser.parse_args()

    main(args)
