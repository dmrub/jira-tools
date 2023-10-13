#!/usr/bin/env python3
import argparse
import configparser
import os
import os.path
import sys
from typing import Optional
from itertools import chain

try:
    from atlassian import Jira
    from ruamel.yaml import YAML
except ModuleNotFoundError as e:
    print("Please install the modules from the requirement.txt file first !\n", file=sys.stderr)
    raise e


def jira_get_issues(jira: Jira, jql: Optional[str], fields="*all"):
    if not jql:
        return
    start = 0
    limit = 200
    total = -1
    while True:
        data = jira.jql(jql, start=start, limit=limit, fields=fields)
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


def jira_get_issues_from_keys(jira: Jira, keys: list[str], fields="*all"):
    if not keys:
        return
    for key in keys:
        yield jira.issue(key, fields=fields)


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

    if args.jql:
        print("JQL: {}".format(args.jql))
    else:
        print("No JQL specified")
    if args.keys:
        print("Jira keys: {}".format(", ".join(args.keys)))
    else:
        print("No Jira keys specified")
    if args.add_labels:
        print("Add labels: {}".format(", ".join(args.add_labels)))
    else:
        print("There are no labels to add")
    if args.remove_labels:
        print("Remove labels: {}".format(", ".join(args.remove_labels)))
    else:
        print("There are no labels to remove")

    if not args.add_labels and not args.remove_labels:
        print("Error: no labels specified for adding and/or removing", file=sys.stderr)
        sys.exit(1)

    jira = Jira(url="https://" + args.atlassian_domain, username=user, password=password)

    num_issues = 0
    num_updated_issues = 0

    for issue_dict in chain(jira_get_issues_from_keys(jira, args.keys), jira_get_issues(jira, args.jql, fields="labels")):
        num_issues += 1
        issue_key = issue_dict.get("key")
        fields = issue_dict.get("fields")
        old_labels = fields.get("labels")

        new_labels = list(old_labels)
        old_labels_set = set(old_labels)
        update_labels = False
        for label in args.add_labels:
            if label not in old_labels_set:
                new_labels.append(label)
                print("Add label {label!r} to the issue {key}".format(label=label, key=issue_key))
                update_labels = True

        for label in args.remove_labels:
            if label in old_labels_set and label in new_labels:
                new_labels.remove(label)
                print("Remove label {label!r} from the issue {key}".format(label=label, key=issue_key))
                update_labels = True

        if update_labels:
            num_updated_issues += 1
            if not args.dry_run:
                print("Update issue {key} with labels: {labels}".format(key=issue_key, labels=", ".join(new_labels)))
                jira.update_issue_field(issue_key, {"labels": new_labels})
            else:
                print(
                    "DRY RUN: I would update issue {key} with labels: {labels}".format(
                        key=issue_key, labels=", ".join(new_labels)
                    )
                )
    print("Processed {} issue(s)".format(num_issues))
    if not args.dry_run:
        print("Updated {} issue(s)".format(num_updated_issues))
    else:
        print("DRY RUN: I would have updated {} issue(s)".format(num_updated_issues))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add labels to jira issues", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-n", "--dry-run", action="store_true", help="perform a trial run with no changes made")
    parser.add_argument(
        "--atlassian-domain",
        type=str,
        metavar="DOMAIN",
        help="Atlassian domain on which the Jira issues will be labeled. "
        "If not specified, value of 'domain' from the DEFAULTS section of the configuration file is used.",
    )
    parser.add_argument(
        "--config-file",
        type=str,
        default="config.ini",
        metavar="FILENAME",
        help="INI configuration file with Atlassian credentials",
    )
    parser.add_argument("--jql", type=str, metavar="JQL_QUERY", help="JQL query to find issues")
    parser.add_argument(
        "--key",
        metavar="ISSUE_KEY",
        type=str,
        dest="keys",
        default=[],
        nargs="+",
        action="extend",
        help="Jira issue keys",
    )
    parser.add_argument(
        "--add",
        metavar="LABEL",
        type=str,
        dest="add_labels",
        default=[],
        nargs="+",
        action="extend",
        help="label(s) to add",
    )
    parser.add_argument(
        "--remove",
        metavar="LABEL",
        type=str,
        dest="remove_labels",
        default=[],
        nargs="+",
        action="extend",
        help="label(s) to remove",
    )

    args = parser.parse_args()

    main(args)
