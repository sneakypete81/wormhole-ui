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
          [],
          exclude_binaries=True,
          name='Magic Wormhole',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               upx_exclude=[],
               name='Magic Wormhole')
app = BUNDLE(coll,
             name='Magic Wormhole.app',
             icon='icons/wormhole.icns',
             bundle_identifier=None,
             info_plist={
                 'NSPrincipalClass': 'NSApplication',
                 'NSRequiresAquaSystemAppearance': 'NO',
                 'NSHighResolutionCapable': 'YES'})
