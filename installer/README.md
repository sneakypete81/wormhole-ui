# Installers

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
  makensis /DPRODUCT_VERSION=0.1.0 installer/windows_installer.nsi
```

The installer is written to the `dist` folder.

## MacOS

First build the .app with PyInstaller. This must be done on a MacOS machine.

```sh
  poetry run pyinstaller installer/macos.spec
```
