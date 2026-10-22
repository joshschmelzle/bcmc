Publishing and Distribution
===========================

Testing
-------

Install depends:

```bash
python -m pip install -U pytest tox
```

Run the test driver:

```
tox
```

Run the formatter:

```
tox -e format
```

Building (setup.py)
-------------------

Install depends:

```bash
python -m pip install -U pip wheel setuptools twine
```

To create a source archive and a wheel for your package, you can run the following command:

```bash
python setup.py sdist bdist_wheel
```

This will create two files in a newly created dist directory, a source archive (.tar.gz) and a wheel (.whl):

Building (pyproject.toml)
-------------------------

Install depends:

```bash
python -m pip install -U pip build pytest setuptools wheel twine
```

To create a source archive and a wheel for your package, you can run the following command:

```bash
python -m build
```

This will create two files in a newly created dist directory, a source archive (.tar.gz) and a wheel (.whl):

Releasing to PyPI
-----------------

bcmc publishes to PyPI from GitHub Actions with [Trusted Publishing](https://docs.pypi.org/trusted-publishers/), so no API token or password is stored anywhere.

1. Bump `__version__` in `bcmc/version.py` and merge it to `main`.
2. Create a GitHub release with a tag that matches the version, e.g. `v0.2.0` for `0.2.0`:

   ```bash
   gh release create v0.2.0 --target main --title v0.2.0 --generate-notes
   ```

3. The `publish` workflow runs the full test matrix, checks that the tag matches `bcmc.__version__`, builds the sdist and wheel, and runs `twine check`.
4. The upload job waits on the `pypi` environment. Approve it in the workflow run on GitHub and it uploads to PyPI.

The PyPI side is configured under the project's Publishing settings: owner `joshschmelzle`, repository `bcmc`, workflow `publish.yml`, environment `pypi`.

Manual upload (fallback)
------------------------

You can run twine check on the files created in dist:

```bash
python -m twine check dist/*
```

Upload to production pypi:

```bash
python -m twine upload dist/*
```

Versioning and Git Tagging
--------------------------

Suggest to use semantic versioning like so:

```bash
v<major>.<minor>.<patch>
```

Where:

- *major* is version number where there are breaking modifications (new version not compatible with previous)
- *minor* is version number compatible with previous versions
- *patch* is an increment for bug fix / hot fix / patch fix on your software

To create a Git tag (on the latest commit (aka HEAD) of current branch) with a message use the following:

```bash
git tag -a <tag_name> -m "message"
```

So if you want a tag on your `main` branch with a message `"new hotfix release for v0.1.42"`:

Confirm branch with `git status | findstr branch` on Windows or `git status | grep branch` *nix.

```bash
git tag -a v0.1.42 -m "new hotfix release for v0.1.42"
```

Verify your Git tag was successfully created:

```bash
git tag
git tag -n
```

Push your tag:

```bash
git push origin <tag>
git push origin v0.1.0
```


