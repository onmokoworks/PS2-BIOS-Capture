# 検証runbook

## Phase 2 — まず固定データ
1. `make -C ps2 SOURCE_KIND=0`、自分の起動環境で通常ELFを実行する。PS2→AV MULTI OUT/composite→capture→PCの配線。送信開始は自動。PS2のUSBとネットワークをデータ転送に使わない。
2. 320×224 non-interlaced/NTSCの四隅finderが全部映るよう調整。参考PNGは`reference-first.png`。画面を覆うOSD、シャープ化、ノイズ低減、色の自動変動を可能なら無効化。240p非対応で黒画面/強制weaveになる機器は別途切り分ける。
3. `python -m receiver --camera 0 --state checkpoints/test --output test-received.bin`。既定で約497 packets、理論約50秒/周。`valid`が増え、次周で欠落が埋まることを確認。
4. `python -m tools.test_pattern expected.bin`を生成し、全byte比較。frame CRC合格だけでは合格としない。
5. 録画を保存する場合、録画ファイル経由でも同じ結果になることを確認。

PCSX2では所有BIOSを利用者が設定し、ELF起動→screenshot/録画→同じreceiverで固定データ一致を確認。内部解像度やpostprocessingを固定し、縦方向の引伸ばしはfinderで補正。これはGS renderer検証でありcompositeやUVCの検証ではない。検証に必要なBIOSをダウンロードしない。

## Phase 3 — ROM0先頭64 KiB
固定データの実機合格後、`SOURCE_KIND=1`をビルド・起動。新規stateを使用し、65536 bytesの完成とsource CRC一致を確認する。snapshotはIOPの0xBFC00000（physical 0x1FC00000のuncached alias）からread-only RPC経由で取得。

IOP bindは最大300 VBlank試行。同期RPC/DMAそのものは壊れたIOP/ハードウェアで停止し得るため、永久停止時は結果を合格扱いしない。エラー時の画面はマゼンタ、正常packet送信を行わない。復元CRCは取得snapshotと受信結果の一致を検査し、ROM読出しの意味的正しさまで証明するものではない。別途所有する既知の正常backupがあればprefix比較を行う。

## Phase 4 — ROM0全4 MiB
Phase 3実機合格後に`SOURCE_KIND=2`。新規stateで4194304 bytes・全31,776 packets・source CRC一致を確認。再起動して2回取得しhashが一致するかも比較すると、読出し再現性を確認できる。ROM0 address/sizeは通常retail PS2向け固定仮定で、特殊機種/TOOLは未検証。

以下を個人の検証記録として残す。BIOSや録画を公開しない。

|項目|記入欄|
|---|---|
|PS2型番/region|未測定|
|起動方法/ELF SHA256|未測定|
|capture型番/driver/backend|未測定|
|入力signalと録画resolution/fps|未測定|
|SOURCE_KIND / HOLD_VBLANKS|未測定|
|有効packets / 欠落 / 周回数 / 時間|未測定|
|source CRC32 / 復元CRC32 / byte数|未測定|
|固定データまたは既知backupとのbyte比較|未測定|
|frame境界 / crop / 色の問題|未測定|

ROM0の実機合格が次のobject拡張のゲート。ROM1/ROM2は機種ごとの存在・サイズ検出、NVMはsceCdReadNVMの16-bit単位読出し、MECはsceCdMVの戻り値仕様をそれぞれ独立して設計する。FreeDVDBootは対応DVD Player versionとライセンス/同梱物を再調査してから別パッケージとして扱う。
