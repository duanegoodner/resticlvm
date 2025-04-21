from resticlvm.utils_run import optional_run, run_with_sudo


def test_run_with_sudo():
    run_with_sudo(cmd=["echo", "Hello, World!"], password="test123")


# def test_optional_run(mocker):
#     # Mock subprocess.run to prevent actual command execution
#     mock_run = mocker.patch("subprocess.run")

#     # Test dry run
#     optional_run(["echo", "Hello, World!"], dry_run=True)
#     mock_run.assert_not_called()

#     # Test actual run
#     optional_run(["echo", "Hello, World!"], dry_run=False)
#     mock_run.assert_called_once_with(["echo", "Hello, World!"], check=True)
#     mock_run.reset_mock()
