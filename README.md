# Jira Tools

This repository contains helpful tools for working with the Atlassian Jira system.

* [jira_download_issues.py](jira_download_issues.py) tool retrieves issues from Atlassian Jira.

* [jira_edit_labels.py](jira_edit_labels.py) tool to add and remove labels to issues in Atlassian Jira.

* [requirements.txt](requirements.txt) python module requirements for all tools.

All tools use credentials loaded from the config.ini file in the working directory (i.e. the directory where you start your script). Path to config.ini file can be changed by using `--config

## [jira_download_issues.py](jira_download_issues.py)

The configuration in the config.ini file should have the following format:
```ini
[<ATLASSIAN_DOMAIN>]
user=<Atlassian Account User>
api_token=<Atlassian API Token>
```

`<ATLASSIAN_DOMAIN>` is the domain provided by Atlassian, e.g  mydomain.atlassian.net .
`<Atlassian Account User>`  is the user you use to log in to our Atlassian Cloud. `<Atlassian API Token>` is the token you can request here: https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/ .

Running `jira_download_issues.py` with the `--help` option will output the help information below:

```
usage: jira_download_issues.py [-h] [--atlassian-domain DOMAIN] [--config-file FILENAME] [--dest-dir DIRECTORY] [--jql JQL] [-f {yaml,text}] [-d]

Download jira issues

options:
  -h, --help            show this help message and exit
  --atlassian-domain DOMAIN
                        Atlassian domain from which the Jira issues are to be downloaded. If not specified, value of 'domain' from the DEFAULTS section of the configuration file is used.
                        (default: None)
  --config-file FILENAME
                        INI configuration file with Atlassian credentials (default: config.ini)
  --dest-dir DIRECTORY  Output directory where the issues will be saved (default: issues)
  --jql JQL             JQL query to find issues.If not specified, value of 'jql' from the DEFAULTS section of the configuration file is used. (default: None)
  -f {yaml,text}, --format {yaml,text}
                        output format (default: text)
  -d, --download-attachments
                        download and store attachments (default: False)
```

## [jira_edit_labels.py](jira_edit_labels.py)

For example, to add the labels X and Z to and remove label W from all issues labeled Y, run the following command:
```sh
jira_edit_labels.py "labels = Y" --add X Z --remove W
```

Running `jira_edit_labels.py` with the `--help` option will output the help information below:

```
usage: jira_edit_labels.py [-h] [-n] [--atlassian-domain DOMAIN] [--config-file FILENAME] [--jql JQL_QUERY] [--key ISSUE_KEY [ISSUE_KEY ...]] [--add LABEL [LABEL ...]]
                           [--remove LABEL [LABEL ...]]

Add labels to jira issues

options:
  -h, --help            show this help message and exit
  -n, --dry-run         perform a trial run with no changes made (default: False)
  --atlassian-domain DOMAIN
                        Atlassian domain on which the Jira issues will be labeled. If not specified, value of 'domain' from the DEFAULTS section of the configuration file is used.
                        (default: None)
  --config-file FILENAME
                        INI configuration file with Atlassian credentials (default: config.ini)
  --jql JQL_QUERY       JQL query to find issues (default: None)
  --key ISSUE_KEY [ISSUE_KEY ...]
                        Jira issue keys (default: [])
  --add LABEL [LABEL ...]
                        label(s) to add (default: [])
  --remove LABEL [LABEL ...]
                        label(s) to remove (default: [])
```

## License

Copyright 2022-2023 Dmitri Rubinstein

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
