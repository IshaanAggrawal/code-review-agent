from github import Github, GithubException
from app.core.config import get_settings
from app.core.exception import GitHubAPIException, PRNotFoundException
from app.core.logger import logger
from app.domain.data_models import PRMetadata, PRFile

settings = get_settings()


class GitHubService:

    def __init__(self):
        self.client = Github(settings.github_token)
        self.repo = self.client.get_repo(
            f"{settings.github_repo_owner}/{settings.github_repo_name}"
        )

    async def get_pr_metadata(self, pr_number: int) -> PRMetadata:
        """Fetch PR metadata."""
        try:
            pr = self.repo.get_pull(pr_number)
            return PRMetadata(
                pr_number=pr.number,
                title=pr.title,
                author=pr.user.login,
                base_branch=pr.base.ref,
                head_branch=pr.head.ref,
                repo_full_name=self.repo.full_name,
                files_changed=pr.changed_files,
                additions=pr.additions,
                deletions=pr.deletions,
                pr_url=pr.html_url,
            )
        except GithubException as e:
            if e.status == 404:
                raise PRNotFoundException(pr_number)
            raise GitHubAPIException(str(e), e.status)

    async def get_pr_files(self, pr_number: int) -> list[PRFile]:
        """Fetch all changed files with diffs."""
        try:
            pr = self.repo.get_pull(pr_number)
            files = []
            for f in pr.get_files():
                files.append(PRFile(
                    filename=f.filename,
                    status=f.status,
                    additions=f.additions,
                    deletions=f.deletions,
                    patch=f.patch,
                ))
            logger.info(f"Fetched {len(files)} files for PR #{pr_number}")
            return files
        except GithubException as e:
            raise GitHubAPIException(str(e), e.status)

    async def post_review_comment(self, pr_number: int, comment: str) -> None:
        """Post final review comment on the PR."""
        try:
            pr = self.repo.get_pull(pr_number)
            pr.create_issue_comment(comment)
            logger.info(f"Review comment posted on PR #{pr_number}")
        except GithubException as e:
            raise GitHubAPIException(f"Failed to post comment: {e}", e.status)