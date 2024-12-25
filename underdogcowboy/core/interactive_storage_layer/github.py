import logging
import time
import requests
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

import asyncio
import aiofiles
import aiohttp


class GithubAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.github_cache_file = Path.home() / '.underdogcowboy' / 'github_cache.json'


    async def _fetch_all_pages(
        self,
        session: aiohttp.ClientSession,
        url: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Helper method to fetch all pages of a GitHub API endpoint.

        Args:
            session (aiohttp.ClientSession): The HTTP session to use for requests.
            url (str): The initial URL to fetch.
            headers (Dict[str, str]): Headers to include in the requests.
            params (Optional[Dict[str, Any]]): Query parameters for the request.

        Returns:
            List[Dict[str, Any]]: Aggregated list of items from all pages.
        """
        all_items = []
        while url:
            try:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        all_items.extend(data)
                        logging.debug(f"Fetched {len(data)} items from {url}. Total so far: {len(all_items)}.")
                        # Parse the 'Link' header for pagination
                        link = response.headers.get("Link", "")
                        url = self._parse_next_link(link)
                        params = None  # Only need to pass params on the first request
                    elif response.status == 403:
                        logging.warning(f"Access forbidden when accessing {url}.")
                        break
                    elif response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", 1))
                        logging.warning(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
                        await asyncio.sleep(retry_after)
                    else:
                        error_text = await response.text()
                        logging.error(f"Failed to fetch data from {url}: {response.status} - {error_text}")
                        break
            except aiohttp.ClientError as e:
                logging.error(f"Client error while fetching {url}: {e}")
                break
            except Exception as e:
                logging.exception(f"Unexpected error while fetching {url}: {e}")
                break
        return all_items

    def _parse_next_link(self, link_header: str) -> Optional[str]:
        """
        Parses the 'Link' header to find the URL for the next page.

        Args:
            link_header (str): The 'Link' header from the HTTP response.

        Returns:
            Optional[str]: The URL for the next page, or None if there are no more pages.
        """
        if not link_header:
            return None
        parts = link_header.split(',')
        for part in parts:
            section = part.split(';')
            if len(section) == 2:
                url_part, rel = section
                url = url_part.strip()[1:-1]
                rel = rel.strip()
                if rel == 'rel="next"':
                    return url
        return None

    async def get_repositories(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch the list of GitHub repositories with adaptive caching (async version).

        This function retrieves repositories accessible to the API key, including:
        - Personal repositories owned by the user.
        - Repositories for organizations the user has access to.

        It uses adaptive caching to reduce redundant API calls:
        - The cache is split into `user_repos` and `org_repos`.
        - Separate TTLs are used for each cache category:
            - User repositories have a shorter TTL (e.g., 20 minutes).
            - Organization repositories have a longer TTL (e.g., 40 minutes).
        - Cache validity is determined by recent user activity.

        API key permissions determine the accessible repositories:
        - 403 Forbidden errors indicate insufficient scope for certain data.
        - If the API key has limited access, the function gracefully skips restricted parts.

        Error Handling:
        - Handles API rate limits (`429 Too Many Requests`) using a `Retry-After` header if provided.
        - Logs meaningful messages for permission issues (e.g., 403 errors) and connection errors.
        - Continues execution even if some sources fail (e.g., missing data for one organization).

        Args:
            force_refresh (bool): If True, bypass the cache and fetch fresh data.

        Returns:
            List[Dict[str, Any]]: A flat list of repositories from both personal and organization scopes.

        Usage Examples:
            # Standard usage with adaptive caching
            repos = await get_repositories()

            # Force refresh to bypass the cache and fetch fresh data
            repos = await get_repositories(force_refresh=True)

        Caching Scenarios:
            - Active Use: If the user has been active recently (within 5 minutes), a shorter TTL is used to fetch more recent data.
            - Idle Periods: During idle times (over 1 hour), a longer TTL reduces API calls.
            - Force Refresh: The cache is bypassed, and fresh data is fetched regardless of activity.

        Note:
            Ensure the API key used has sufficient permissions to access the desired data.
            Handle rate limits and API errors in production scenarios for smooth operation.
        """
        # Define cache TTLs
        user_cache_ttl = 20 * 60  # 20 minutes for user repositories
        org_cache_ttl = 40 * 60   # 40 minutes for organization repositories
        current_time = time.time()

        # Load cache if it exists
        if self.github_cache_file.exists():
            try:
                async with aiofiles.open(self.github_cache_file, 'r') as f:
                    cache_content = await f.read()
                cache = json.loads(cache_content)
                logging.debug("Cache loaded successfully.")
            except aiofiles.oserrors.OSError as e:
                logging.error(f"Error reading cache file: {e}")
                cache = {
                    "user_repos": [],
                    "org_repos": {},
                    "last_user_update": 0,
                    "last_org_update": {},
                    "last_active": 0
                }
                logging.info("Initialized empty cache due to read error.")
            except json.JSONDecodeError as e:
                logging.error(f"JSON decode error: {e}")
                cache = {
                    "user_repos": [],
                    "org_repos": {},
                    "last_user_update": 0,
                    "last_org_update": {},
                    "last_active": 0
                }
                logging.info("Reinitialized cache due to JSON decode error.")
        else:
            cache = {
                "user_repos": [],
                "org_repos": {},
                "last_user_update": 0,
                "last_org_update": {},
                "last_active": 0
            }
            logging.info("Cache file does not exist. Initialized empty cache.")

        # Ensure 'last_org_update' exists
        if "last_org_update" not in cache:
            cache["last_org_update"] = {}
            logging.debug("'last_org_update' key was missing in cache. Initialized as empty dict.")

        # Define cache validity
        user_cache_valid = (
            not force_refresh and 
            current_time - cache.get("last_user_update", 0) < user_cache_ttl
        )
        org_cache_valid = lambda org: (
            not force_refresh and 
            (current_time - cache.get("last_org_update", {}).get(org, 0) < org_cache_ttl)
        )

        # Fetch data if necessary
        headers = {"Authorization": f"token {self.api_key}"}
        updated_user_repos = False
        updated_org_repos = False

        async with aiohttp.ClientSession() as session:
            # Fetch user's personal repositories if cache is invalid
            if not user_cache_valid:
                user_repos_url = "https://api.github.com/user/repos"
                try:
                    user_repos = await self._fetch_all_pages(session, user_repos_url, headers)
                    if user_repos:
                        cache["user_repos"] = user_repos
                        cache["last_user_update"] = current_time
                        updated_user_repos = True
                        logging.info("User repositories fetched and cache updated.")
                except Exception as e:
                    logging.exception(f"Error fetching user repositories: {e}")

            # Fetch organizations and their repositories
            orgs_url = "https://api.github.com/user/orgs"
            try:
                orgs = await self._fetch_all_pages(session, orgs_url, headers)
                logging.info(f"Fetched {len(orgs)} organizations.")
                for org in orgs:
                    org_name = org.get("login")
                    if not org_name:
                        logging.warning("Organization without a login name encountered. Skipping.")
                        continue
                    if not org_cache_valid(org_name):
                        org_repos_url = f"https://api.github.com/orgs/{org_name}/repos"
                        try:
                            org_repos = await self._fetch_all_pages(session, org_repos_url, headers)
                            if org_repos:
                                cache["org_repos"][org_name] = org_repos
                                cache["last_org_update"][org_name] = current_time
                                updated_org_repos = True
                                logging.info(f"Repositories for organization '{org_name}' fetched and cache updated.")
                        except Exception as e:
                            logging.exception(f"Error fetching repos for organization '{org_name}': {e}")
            except Exception as e:
                logging.exception(f"Error fetching organizations: {e}")

        # Update cache activity timestamp
        if updated_user_repos or updated_org_repos:
            cache["last_active"] = current_time
            try:
                self.github_cache_file.parent.mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(self.github_cache_file, 'w') as f:
                    await f.write(json.dumps(cache, indent=2))
                logging.debug("Cache file updated successfully.")
            except aiofiles.oserrors.OSError as e:
                logging.error(f"Error writing to cache file: {e}")
            except Exception as e:
                logging.exception(f"Unexpected error writing to cache file: {e}")

        # Combine and return results as a flat list
        combined_repos = cache.get("user_repos", []) + [
            repo for repos in cache.get("org_repos", {}).values() for repo in repos
        ]
        logging.debug(f"Total repositories fetched: {len(combined_repos)}")
        return combined_repos

    def get_open_issues(self, repo_owner, repo_name):
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/issues"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            issues = response.json()
            open_issues = [issue for issue in issues if issue.get('state') == 'open']
            return open_issues
        else:
            print(f"Failed to fetch issues: {response.status_code}")
            return []

    def comment_on_issue(self, repo_owner, repo_name, issue_number, comment):
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/issues/{issue_number}/comments"
        data = {"body": comment}
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code == 201:
            print(f"Successfully commented on issue #{issue_number}")
        else:
            print(f"Failed to comment on issue #{issue_number}: {response.status_code}, {response.text}")

    def create_issue(self, repo_owner, repo_name, title, body):
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/issues"
        data = {
            "title": title,
            "body": body,
            "assignees": [self.username]
        }
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code == 201:
            print(f"Successfully created issue '{title}'")
            return response.json()
        else:
            print(f"Failed to create issue '{title}': {response.status_code}, {response.text}")
            return None

    def list_labels(self, repo_owner, repo_name):
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/labels"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            labels = response.json()
            return labels
        else:
            print(f"Failed to fetch labels: {response.status_code}")
            return []

    def add_labels_to_issue(self, repo_owner, repo_name, issue_number, labels):
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/issues/{issue_number}/labels"
        data = {"labels": labels}
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code == 200:
            print(f"Successfully added labels to issue #{issue_number}")
        else:
            print(f"Failed to add labels to issue #{issue_number}: {response.status_code}, {response.text}")

    def remove_label_from_issue(self, repo_owner, repo_name, issue_number, label):
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/issues/{issue_number}/labels/{label}"
        response = requests.delete(url, headers=self.headers)
        if response.status_code == 200:
            print(f"Successfully removed label '{label}' from issue #{issue_number}")
        else:
            print(f"Failed to remove label '{label}' from issue #{issue_number}: {response.status_code}, {response.text}")

    def get_projects(self, repo_owner, repo_name):
        query = """
        query($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            projectsV2(first: 20) {
              nodes {
                id
                title
                shortDescription
                url
                closed
                items(first: 10) {
                  nodes {
                    id
                    type
                    fieldValues(first: 10) {
                      nodes {
                        ... on ProjectV2ItemFieldTextValue {
                          text
                          field {
                            ... on ProjectV2FieldCommon {
                              name
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        variables = {"owner": repo_owner, "name": repo_name}
        response = requests.post(self.graphql_url, headers=self.headers, json={"query": query, "variables": variables})
        if response.status_code == 200:
            result = response.json()
            if "errors" in result:
                print(f"GraphQL Errors: {result['errors']}")
                return []
            return result["data"]["repository"]["projectsV2"]["nodes"]
        else:
            print(f"Failed to fetch projects: {response.status_code}, {response.text}")
            return []

    def create_project(self, project_name, columns):
        mutation = """
        mutation($ownerId: ID!, $projectName: String!) {
          createProjectV2(input: {ownerId: $ownerId, title: $projectName}) {
            projectV2 {
              id
              title
              url
            }
          }
        }
        """
        variables = {
            "ownerId": self.owner_id,
            "projectName": project_name
        }
        response = requests.post(
            self.graphql_url,
            headers=self.headers,
            json={"query": mutation, "variables": variables}
        )
        if response.status_code == 200:
            result = response.json()
            if "errors" in result:
                print(f"GraphQL Errors: {result['errors']}")
                print(f"Full Response: {result}")  # For debugging
                return None
            project = result["data"]["createProjectV2"]["projectV2"]
            print(f"Successfully created project '{project_name}' with URL: {project['url']}")
            project_id = project["id"]
            print(f"Project ID: {project_id}")  # Debugging information

            # Add columns (fields) to the project using Project V2 mutation
            for column in columns:
                self.add_column_to_project_v2(project_id, column)

            return project
        else:
            print(f"Failed to create project: {response.status_code}, {response.text}")
            return None

    def add_column_to_project_v2(self, project_id, column_name):
        mutation = """
        mutation($projectId: ID!, $input: ProjectV2CreateFieldInput!) {
          projectV2CreateField(projectId: $projectId, input: $input) {
            projectV2Field {
              id
              name
              dataType
            }
          }
        }
        """
        variables = {
            "projectId": project_id,
            "input": {
                "name": column_name,
                "dataType": "SINGLE_SELECT"  # Adjust the dataType as needed
            }
        }
        response = requests.post(
            self.graphql_url,
            headers=self.headers,
            json={"query": mutation, "variables": variables}
        )
        if response.status_code == 200:
            result = response.json()
            if "errors" in result:
                print(f"GraphQL Errors: {result['errors']}")
                print(f"Full Response: {result}")  # For debugging
                return None
            field = result["data"]["projectV2CreateField"]["projectV2Field"]
            print(f"Successfully added field '{column_name}' to project")
            return field
        else:
            print(f"Failed to add field '{column_name}' to project: {response.status_code}, {response.text}")
            return None
