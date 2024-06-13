import requests
import json
import os
import time
import base64

GITHUB_TOKEN = 'YOUR_GITHUB_TOKEN'
HEADERS = {'Authorization': f'token {GITHUB_TOKEN}'}


def fetch_repositories(query, max_repos=2000):
    repos = []
    page = 1
    per_page = 100  # maximum allowed by GitHub API

    while len(repos) < max_repos:
        url = f'https://api.github.com/search/repositories?q={query}+language:Java&sort=stars&order=desc&page={page}&per_page={per_page}'
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            repos.extend(data['items'])
        else:
            print(f"Failed to fetch repositories: {response.status_code} {response.text}")
            break

        if 'next' not in response.links:
            break

        page += 1
        time.sleep(1)  # to avoid hitting the rate limit

    return repos[:max_repos]


def fetch_files(repo_full_name, path=''):
    url = f'https://api.github.com/repos/{repo_full_name}/contents/{path}'
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch files for {repo_full_name} at {path}: {response.status_code} {response.text}")
        return []


def fetch_file_content(url):
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        content = response.json().get('content', '')
        return base64.b64decode(content).decode('utf-8') if content else ''
    else:
        print(f"Failed to fetch file content: {response.status_code} {response.text}")
        return ''


def collect_java_files_from_repo(repo):
    java_files = []
    files = fetch_files(repo['full_name'])
    for file in files:
        if file['type'] == 'file' and file['name'].endswith('.java'):
            content = fetch_file_content(file['url'])
            java_files.append({'name': file['name'], 'path': file['path'], 'content': content})
        elif file['type'] == 'dir':
            subfiles = fetch_files(repo['full_name'], file['path'])
            for subfile in subfiles:
                if subfile['type'] == 'file' and subfile['name'].endswith('.java'):
                    content = fetch_file_content(subfile['url'])
                    java_files.append({'name': subfile['name'], 'path': subfile['path'], 'content': content})
    return java_files


def save_state(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


def load_state(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}


def main():
    repos = fetch_repositories('java', max_repos=2000)
    state_filename = 'state.json'
    json_filename = 'java_code_dataset.json'

    state = load_state(state_filename)
    processed_repos = state.get('processed_repos', [])
    all_java_files = state.get('all_java_files', [])

    for repo in repos:
        if repo['full_name'] in processed_repos:
            print(f"Skipping already processed repository: {repo['full_name']}")
            continue

        print(f"Processing repository: {repo['full_name']}")
        java_files = collect_java_files_from_repo(repo)
        all_java_files.extend(java_files)

        processed_repos.append(repo['full_name'])
        state = {
            'processed_repos': processed_repos,
            'all_java_files': all_java_files
        }

        save_state(state, state_filename)
        save_state(all_java_files, json_filename)
        print(f"Updated {json_filename} with {len(java_files)} new files from {repo['full_name']}")

    print(f"Saved {len(all_java_files)} Java files to {json_filename}")


if __name__ == '__main__':
    main()
