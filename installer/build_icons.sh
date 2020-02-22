rm -rf installer/icons/.build

echo "Building wormhole.icns..."
mkdir -p installer/icons/.build/wormhole.iconset
cp installer/icons/icon16.png installer/icons/.build/wormhole.iconset/icon_16x16.png
cp installer/icons/icon32.png installer/icons/.build/wormhole.iconset/icon_16x16@2x.png
cp installer/icons/icon32.png installer/icons/.build/wormhole.iconset/icon_32x32.png
cp installer/icons/icon64.png installer/icons/.build/wormhole.iconset/icon_32x32@2x.png
cp installer/icons/icon64.png installer/icons/.build/wormhole.iconset/icon_64x64.png
cp installer/icons/icon128.png installer/icons/.build/wormhole.iconset/icon_64x64@2x.png
cp installer/icons/icon128.png installer/icons/.build/wormhole.iconset/icon_128x128.png
cp installer/icons/icon256.png installer/icons/.build/wormhole.iconset/icon_128x128@2x.png
cp installer/icons/icon256.png installer/icons/.build/wormhole.iconset/icon_256x256.png
iconutil -c icns installer/icons/.build/wormhole.iconset/ -o installer/icons/wormhole.icns

echo "Building wormhole.ico..."
mkdir -p installer/icons/.build/wormhole.iconwin
cp installer/icons/icon16.png installer/icons/.build/wormhole.iconwin
cp installer/icons/icon24.png installer/icons/.build/wormhole.iconwin
cp installer/icons/icon32.png installer/icons/.build/wormhole.iconwin
cp installer/icons/icon48.png installer/icons/.build/wormhole.iconwin
cp installer/icons/icon64.png installer/icons/.build/wormhole.iconwin
cp installer/icons/icon128.png installer/icons/.build/wormhole.iconwin
cp installer/icons/icon256.png installer/icons/.build/wormhole.iconwin
npx @fiahfy/ico-convert installer/icons/.build/wormhole.iconwin/ installer/icons/wormhole.ico
