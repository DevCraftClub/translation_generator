from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from assets.pipeline import run_generator


CONFIG_PATH = ROOT_DIR / ".github" / "translation-repos.yml"
BRANCH_NAME = "i18-generated"


def main():
	token = os.environ.get("GH_PAT")
	if not token:
		raise SystemExit("GH_PAT is not set.")

	repos = load_yaml(CONFIG_PATH).get("repos", [])
	failures = []
	for repo_config in repos:
		try:
			process_repository(repo_config, token)
		except Exception as exc:  # noqa: BLE001
			failures.append(f"{repo_config.get('name', repo_config.get('repository'))}: {exc}")

	if failures:
		raise SystemExit("Failed repositories:\n- " + "\n- ".join(failures))


def process_repository(repo_config, token):
	repo_url = repo_config["repository"]
	owner, repo_name = parse_repository(repo_url)
	default_branch = github_request_json(f"/repos/{owner}/{repo_name}", token)["default_branch"]

	with tempfile.TemporaryDirectory(prefix="translation-generator-") as temp_dir:
		repo_dir = Path(temp_dir) / repo_name
		clone_repository(repo_url, repo_dir, token)
		run_git(repo_dir, "checkout", "-B", BRANCH_NAME, f"origin/{default_branch}")

		crowdin_config = load_yaml(repo_dir / repo_config["config"])
		generation_jobs = collect_generation_jobs(repo_dir, repo_config, crowdin_config, repo_name)
		for job in generation_jobs:
			output_file = run_generator(
					source=repo_dir / job["source"],
					output=repo_dir / job["output"],
					module=job["module"],
					lang=job["lang"],
					exceptions=[],
					debug=False,
			)
			print(f"[{repo_config['name']}] generated {output_file.relative_to(repo_dir)}")

		if not has_changes(repo_dir):
			print(f"[{repo_config['name']}] no changes")
			return

		run_git(repo_dir, "config", "user.name", "translation-generator[bot]")
		run_git(repo_dir, "config", "user.email", "translation-generator[bot]@users.noreply.github.com")
		run_git(repo_dir, "add", ".")
		run_git(repo_dir, "commit", "-m", "chore(i18): regenerate source xliff")
		push_branch(repo_dir, owner, repo_name, token)
		ensure_pull_request(owner, repo_name, default_branch, token, repo_config["name"])


def collect_generation_jobs(repo_dir, repo_config, crowdin_config, repo_name):
	jobs = []
	seen = set()
	module = repo_config.get("trans_file") or repo_name
	for file_config in crowdin_config.get("files", []):
		source_pattern = file_config.get("source")
		if not source_pattern:
			continue
		normalized_pattern = source_pattern.lstrip("/")
		pattern_path = PurePosixPath(normalized_pattern)
		if len(pattern_path.parts) < 2:
			continue

		lang = pattern_path.parent.name
		output_root = str(Path(*pattern_path.parent.parent.parts))
		key = (repo_config["source"], output_root, lang, module)
		if key in seen:
			continue
		seen.add(key)
		jobs.append(
				{
						"source": repo_config["source"],
						"output": output_root,
						"lang": lang,
						"module": module,
				}
		)
	return jobs


def ensure_pull_request(owner, repo_name, default_branch, token, repo_label):
	head = f"{owner}:{BRANCH_NAME}"
	existing = github_request_json(
			f"/repos/{owner}/{repo_name}/pulls?state=open&head={head}",
			token,
	)
	if existing:
		print(f"[{repo_label}] pull request already open: {existing[0]['html_url']}")
		return

	payload = {
			"title": "chore(i18): regenerate source xliff",
			"head": BRANCH_NAME,
			"base": default_branch,
			"body": "Automatisch erzeugte Aktualisierung der Quell-XLIFF-Dateien.",
	}
	created = github_request_json(f"/repos/{owner}/{repo_name}/pulls", token, method="POST", body=payload)
	print(f"[{repo_label}] pull request created: {created['html_url']}")


def push_branch(repo_dir, owner, repo_name, token):
	remote_url = f"https://x-access-token:{token}@github.com/{owner}/{repo_name}.git"
	run_git(repo_dir, "remote", "set-url", "origin", remote_url)
	run_git(repo_dir, "push", "--force-with-lease", "origin", BRANCH_NAME)


def clone_repository(repo_url, repo_dir, token):
	owner, repo_name = parse_repository(repo_url)
	auth_url = f"https://x-access-token:{token}@github.com/{owner}/{repo_name}.git"
	subprocess.run(
			["git", "clone", "--depth", "1", auth_url, str(repo_dir)],
			check=True,
			text=True,
	)


def has_changes(repo_dir):
	result = subprocess.run(
			["git", "-C", str(repo_dir), "status", "--porcelain"],
			check=True,
			text=True,
			capture_output=True,
	)
	return bool(result.stdout.strip())


def run_git(repo_dir, *args):
	subprocess.run(["git", "-C", str(repo_dir), *args], check=True, text=True)


def load_yaml(path):
	with Path(path).open(encoding="utf-8") as handle:
		return yaml.safe_load(handle) or {}


def parse_repository(repo_url):
	parsed = urlparse(repo_url)
	parts = parsed.path.removeprefix("/").removesuffix(".git").split("/")
	if len(parts) != 2:
		raise ValueError(f"Unsupported repository url: {repo_url}")
	return parts[0], parts[1]


def github_request_json(path, token, method="GET", body=None):
	request = Request(
			f"https://api.github.com{path}",
			method=method,
			headers={
					"Accept": "application/vnd.github+json",
					"Authorization": f"Bearer {token}",
					"X-GitHub-Api-Version": "2022-11-28",
			},
	)
	if body is not None:
		request.data = json.dumps(body).encode("utf-8")
		request.add_header("Content-Type", "application/json")

	try:
		with urlopen(request) as response:
			return json.loads(response.read().decode("utf-8"))
	except HTTPError as exc:
		details = exc.read().decode("utf-8", errors="replace")
		raise RuntimeError(f"GitHub API error {exc.code}: {details}") from exc


if __name__ == "__main__":
	main()
