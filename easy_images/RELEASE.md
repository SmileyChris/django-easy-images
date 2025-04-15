# Releasing

To roll a release, make sure you have your PyPI credentials in your keyring and that you have the ``keyring`` tool installed.

## Publishing to PyPI

Tag the current release and push it:

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push --tags
```

Then run:

```bash
rm -rf dist
uv build
uv publish
```


## Adding your credentials to the keyring

Install keyring (used by uv for publishing) and set your credentials:

```bash
uv tool install keyring
keyring set 'https://upload.pypi.org/legacy/' __token__
```

Next, add these environment variables:

```
UV_KEYRING_PROVIDER=subprocess
UV_PUBLISH_USERNAME=__token__
```
