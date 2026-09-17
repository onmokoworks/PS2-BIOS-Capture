# Verification status — 2026-09-17 JST

## 実施結果
**28 tests passed、skipなし、36.83秒。実PS2/PCSX2/UVC機器の検証は未実施。**

環境: Windows、Python 3.11、NumPy 2.4.6、OpenCV headless 5.0.0.93、pytest 9.1.1。host CはGCC（-std=c99 -O2 -Wall -Wextra -Werror）。機械可読結果: [test-results.xml](test-results.xml)。

- 0 / 1 / 131 / 132 / 133 / 4096 / 65536 bytesの画像roundtrip。
- seed固定のrandom 4 MiBを31,776枚のsynthetic RGB frameとして全復号し、source CRCと全byte一致。約34秒。4 MiB分のPNGをディスクへ保存するテストではなく、メモリ内で1枚ずつrender/decodeする。
- PNG保存/読込、逆順/重複、1周目の3枚に1枚dropを後続周回で補完、disk stateからの再開。
- Gaussian blur 5×5 sigma0.7、brightness ×0.72+18、RGB gain=[1.08,0.86,0.96]/offset=[5,9,-4]、crop上5/下4/左7/右6 pixels、653×471へのscale。それぞれと全組合せで4096 bytes全一致。
- 640×448 MJPEG/AVIを実際にencodeしてOpenCV動画adapterから復元。
- CLI reference encoder→PNG directory→CLI receiver→binary比較。既存outputの上書き拒否。
- UVC adapterのdevice index/RGB変換/close時releaseはmock試験。実UVCとは区別する。
- packet全180 bytesを個別に1bit破損させ拒否。CRC付きの不正count/offset/index/size/typeも拒否。異session、矛盾する重複、誤source CRC、不完全転送、frame切替途中の混合画像も拒否。
- PS2用portable CとPythonで、空・端数・最終frame等6ケースのpacket全byte、320×224全pixelが一致。
- PS2既定xorshift32の64 KiBをC/Pythonで一致確認。既知source CRC32 = **4B07E436**。

これらの劣化パラメータは試験条件であり、NTSC composite伝送の完全な物理モデルではない。chroma帯域制限/dot crawl/field mixing/時間方向の色変動は実測が必要。

## PS2ビルド
公式PS2DEV Windows archive（識別hashはREFERENCES参照）のGCC 15.2.0でEEとIOPをビルド。SOURCE_KIND=0,1,2をすべて-Wall -Wextra -Werrorでリンク成功。ELFは32-bit little-endian MIPS PS2向け。

[build manifest](../ps2/build/manifest.json)に3 ELFのサイズとSHA256、同directoryにビルドlogを保存（ソースZIPでは生成物を除外）。モードを連続変更しても確実に再リンクするようにした。これは実行検証を意味しない。

## フェーズごとの到達点
|Phase|実機なしで実施済み|PCSX2で確認する項目（未実施）|実PS2＋captureで確認する項目（未実施）|判定|
|---|---|---|---|---|
|1: host COLOR4|28件のprotocol/画像/CLI/C比較試験、4 MiB全一致|不要|劣化モデルの実測妥当性|host MVP完了|
|2: GS固定データ|portable Cの全pixel一致、TEST ELFビルド|ELF起動・GS画角・screenshot復号・周回|NTSC 240p受付、色校正、固定64 KiB全一致|実装/ビルド済、映像ゲート未合格|
|3: ROM0 64 KiB|read-only Sysman RPC/IOP IRX統合、ELFビルド|emulated ROM snapshot・RPC動作|実ROM読出し、DMA/cache整合性、64 KiB転送|実装/ビルド済、実ROM未検証|
|4: ROM0 4 MiB|同層の4 MiBモード、ELFビルド、synthetic4 MiB|emulated ROM全体の転送|実ROM全4 MiB、復元サイズ/CRC完全一致|実装/ビルド済、完成条件は未達|

Phase 2の実機試験→Phase 3→Phase 4の順を維持する。ROM1/ROM2/NVM/MECとFreeDVDBoot packagingは未実装。ゲート記録は[HARDWARE.md](HARDWARE.md)を使用する。
