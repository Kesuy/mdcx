import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts import ensure_release as release


class ReleaseRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tag = None
        self.published = None
        self.runs = []
        self.writes = []
        self.fail_dispatch = False
        self.version = "4.0.21"
        self.base_version = "4.0.20"
        self.patches = [
            patch.object(release, "git", return_value="merge-sha"),
            patch.object(
                release, "version_at", side_effect=lambda ref: self.base_version if ref.endswith("^1") else self.version
            ),
            patch.object(release, "api", side_effect=self.api),
        ]
        for mock in self.patches:
            mock.start()
            self.addCleanup(mock.stop)

    def api(self, path, data=None, **kwargs):
        if data is not None:
            self.writes.append((path, data))
            if path == "git/refs":
                self.tag = {"object": {"type": "commit", "sha": data["sha"]}}
            elif path.endswith("/dispatches") and self.fail_dispatch:
                raise RuntimeError("dispatch unavailable")
            return None
        if path.startswith("git/ref/tags/"):
            return self.tag
        if path.startswith("git/tags/"):
            return {"object": {"type": "commit", "sha": "merge-sha"}}
        if path.startswith("releases/tags/"):
            return self.published
        if "/runs?" in path:
            return {"workflow_runs": self.runs}
        raise AssertionError(path)

    def test_new_version_creates_tag_and_dispatches_on_tag(self):
        release.ensure_release("merge-sha")
        self.assertEqual([p for p, _ in self.writes], ["git/refs", "actions/workflows/release.yml/dispatches"])
        self.assertEqual(self.writes[-1][1]["ref"], "4.0.21")

    def test_retry_after_dispatch_failure_reuses_tag(self):
        self.fail_dispatch = True
        with self.assertRaisesRegex(RuntimeError, "dispatch unavailable"):
            release.ensure_release("merge-sha")
        self.fail_dispatch = False
        release.ensure_release("merge-sha")
        self.assertEqual(sum(path == "git/refs" for path, _ in self.writes), 1)
        self.assertEqual(sum(path.endswith("/dispatches") for path, _ in self.writes), 2)

    def test_published_release_does_not_dispatch(self):
        self.tag = {"object": {"type": "commit", "sha": "merge-sha"}}
        self.published = {"draft": False}
        release.ensure_release("merge-sha")
        self.assertEqual(self.writes, [])

    def test_draft_release_can_resume(self):
        self.tag = {"object": {"type": "commit", "sha": "merge-sha"}}
        self.published = {"draft": True}
        release.ensure_release("merge-sha")
        self.assertEqual(len(self.writes), 1)

    def test_running_or_queued_release_is_not_duplicated(self):
        self.tag = {"object": {"type": "commit", "sha": "merge-sha"}}
        for status in ["queued", "in_progress", "waiting", "pending", "requested"]:
            with self.subTest(status=status):
                self.runs = [{"status": status}]
                release.ensure_release("merge-sha")
                self.assertEqual(self.writes, [])

    def test_failed_completed_run_can_retry(self):
        self.tag = {"object": {"type": "commit", "sha": "merge-sha"}}
        self.runs = [{"status": "completed", "conclusion": "failure"}]
        release.ensure_release("merge-sha")
        self.assertEqual(len(self.writes), 1)

    def test_conflicting_tag_fails_without_writes(self):
        self.tag = {"object": {"type": "commit", "sha": "different-sha"}}
        with self.assertRaisesRegex(ValueError, "different commit"):
            release.ensure_release("merge-sha")
        self.assertEqual(self.writes, [])

    def test_annotated_tag_is_resolved(self):
        self.tag = {"object": {"type": "tag", "sha": "tag-object"}}
        release.ensure_release("merge-sha")
        self.assertEqual(len(self.writes), 1)

    def test_unchanged_version_does_not_release_ordinary_pr(self):
        self.base_version = self.version
        release.ensure_release("merge-sha")
        self.assertEqual(self.writes, [])
        release.api.assert_not_called()

    def test_wrong_checkout_fails_before_api(self):
        with self.assertRaisesRegex(ValueError, "Checkout"):
            release.ensure_release("other-sha")
        release.api.assert_not_called()


class ParsingAndApiTests(unittest.TestCase):
    def test_version_is_read_without_executing_module(self):
        with patch.object(release, "git", return_value='raise RuntimeError()\nLOCAL_VERSION = "4.0.21"'):
            self.assertEqual(release.version_at("HEAD"), "4.0.21")

    def test_invalid_version_rejected(self):
        for source in ['LOCAL_VERSION = "bad"', "LOCAL_VERSION = 123", "x = 1"]:
            with self.subTest(source=source), patch.object(release, "git", return_value=source):
                with self.assertRaises(ValueError):
                    release.version_at("HEAD")

    def test_only_404_is_treated_as_missing(self):
        with patch.dict(release.os.environ, {"GH_TOKEN": "test", "GITHUB_REPOSITORY": "test/repo"}):
            for code in [401, 403, 429, 500, 404]:
                with (
                    self.subTest(code=code),
                    patch.object(release, "urlopen", side_effect=HTTPError("url", code, "error", {}, None)),
                ):
                    if code == 404:
                        self.assertIsNone(release.api("git/ref/tags/1.0", missing_ok=True))
                    else:
                        with self.assertRaises(HTTPError):
                            release.api("git/ref/tags/1.0", missing_ok=True)


if __name__ == "__main__":
    unittest.main()
