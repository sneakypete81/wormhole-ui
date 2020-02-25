# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['../scripts/run.py'],
             pathex=[],
             binaries=[],
             datas=[('../wormhole_ui/widgets/ui/*.ui', 'wormhole_ui/widgets/ui')],
             hiddenimports=['PySide2.QtXml'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='Magic Wormhole',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          icon='../wormhole_ui/resources/wormhole.ico' )

# Settings without --onefile
#exe = EXE(pyz,
#          a.scripts,
#          [],
#          exclude_binaries=True,
#          name='Magic Wormhole',
#          debug=False,
#          bootloader_ignore_signals=False,
#          strip=False,
#          upx=False,
#          console=False,
#          icon='../wormhole_ui/resources/wormhole.ico' )
#coll = COLLECT(exe,
#               a.binaries,
#               a.zipfiles,
#               a.datas,
#               upx=False,
#               strip=False,
#               upx_exclude=[],
#               name='Magic Wormhole')
