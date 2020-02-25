rm -rf build/icons

echo "Building wormhole.icns..."
mkdir -p build/icons/wormhole.iconset
cp wormhole_ui/resources/icon16.png build/icons/wormhole.iconset/icon_16x16.png
cp wormhole_ui/resources/icon32.png build/icons/wormhole.iconset/icon_16x16@2x.png
cp wormhole_ui/resources/icon32.png build/icons/wormhole.iconset/icon_32x32.png
cp wormhole_ui/resources/icon64.png build/icons/wormhole.iconset/icon_32x32@2x.png
cp wormhole_ui/resources/icon64.png build/icons/wormhole.iconset/icon_64x64.png
cp wormhole_ui/resources/icon128.png build/icons/wormhole.iconset/icon_64x64@2x.png
cp wormhole_ui/resources/icon128.png build/icons/wormhole.iconset/icon_128x128.png
cp wormhole_ui/resources/icon256.png build/icons/wormhole.iconset/icon_128x128@2x.png
cp wormhole_ui/resources/icon256.png build/icons/wormhole.iconset/icon_256x256.png
iconutil -c icns build/icons/wormhole.iconset/ -o wormhole_ui/resources/wormhole.icns

echo "Building wormhole.ico..."
mkdir -p build/icons/wormhole.iconwin
cp wormhole_ui/resources/icon16.png build/icons/wormhole.iconwin
cp wormhole_ui/resources/icon24.png build/icons/wormhole.iconwin
cp wormhole_ui/resources/icon32.png build/icons/wormhole.iconwin
cp wormhole_ui/resources/icon48.png build/icons/wormhole.iconwin
cp wormhole_ui/resources/icon64.png build/icons/wormhole.iconwin
cp wormhole_ui/resources/icon128.png build/icons/wormhole.iconwin
cp wormhole_ui/resources/icon256.png build/icons/wormhole.iconwin
npx @fiahfy/ico-convert build/icons/wormhole.iconwin/ wormhole_ui/resources/wormhole.ico
