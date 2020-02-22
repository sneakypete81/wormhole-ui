# Installers

## Release Procedure

* Update `CHANGELOG.md`
* Update version in `pyproject.toml` and `wormhole_ui/__init__.py`.
* Build installers (see below)
* Test installers
* Commit, tag and push
* Publish to PyPI with `poetry publish`
* Create a release on Github, including the changelog and installers

## Windows
First build the executable with PyInstaller. This must be done on a Windows machine.

```sh
  poetry run pyinstaller installer/windows.spec
```

This currently builds a --onefile bundle, since otherwise there's a proliferation of
console windows whenever the wormhole connects.

Then build the installer with [NSIS](https://nsis.sourceforge.io) v3.05.
This can be done on any platform.

```sh
  makensis -DPRODUCT_VERSION=0.1.0 installer/windows_installer.nsi
```

The installer is written to the `dist` folder.

## MacOS

Set up a High Sierra VM in Virualbox:

  Download the OS installer:
  https://apps.apple.com/gb/app/macos-high-sierra/id1246284741?mt=12

  Create an ISO:
  https://www.whatroute.net/installerapp2iso.html

  Setup ssh port forwarding and remote login:
  https://medium.com/@twister.mr/installing-macos-to-virtualbox-1fcc5cf22801

To copy files in and out of the VM:

```sh
  rsync wormhole-ui sneakypete81@127.0.0.1:~/Projects/ --rsh='ssh -p2222' -r -v --exclude=".git" --exclude=".tox" --exclude="build" --exclude="dist"

  scp -P 2222 -r sneakypete81@127.0.0.1:~/Projects/wormhole-ui/dist/* wormhole-ui/dist

```

First build the .app with PyInstaller. This must be done on a MacOS machine, ideally an old OS version such as the VM set up above.

```sh
  poetry run pyinstaller installer/macos.spec
```

Then build the installer with dmgbuild.

```sh
  poetry run dmgbuild -s installer/macos_installer.py . .
```

The DMG is written to the `dist` folder.

## Icons
The icons have been drawn in Inkscape and exported to various PNG sizes.

Rebuild the .icns and .ico iconsets with the following:

```sh
  installer/build_icons.sh
```
