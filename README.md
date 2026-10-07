# PS2 BIOS Capture

PS2の映像出力からデータを送り、PCのキャプチャボードで受信・復元する実験プロジェクトです。所有するPS2のBIOSをバックアップするために作っています。BIOS本体は同梱・配布しません。

PS2側はデータを4色のセルで表示し、PC側は各フレームとデータ全体のCRC32を確認します。送信は周回するので、欠落したフレームを次の周回から補完できます。転送にUSBストレージやネットワークは使いません。

## 現在の状態

実PS2で固定テストデータ64 KiBの転送に成功し、元データとの完全一致を確認しました。BIOSの読み出し、新しい操作メニュー、高密度グリッドは実機未検証です。ホスト側では全4 MiBの復元を含む50件のテストが通っています。

## PC側の準備

Python 3.11以降を使います。リポジトリのルートで実行します。

```sh
python -m venv .venv
```

Windows PowerShellでは `.venv/Scripts/Activate.ps1`、Linux/macOSでは `source .venv/bin/activate` で環境を有効にします。

```sh
python -m pip install -r requirements-gui.txt
python -m receiver.gui
```

Windowsではセットアップ後に `Launch-Capture.cmd` からも起動できます。キャプチャボードを選んで「受信開始」を押すと、プレビュー、受信バイト数、欠落位置、CRCエラーを表示します。全体CRCが一致すると復元したファイルを保存します。保存先の既定値は `captures/` です。

OBSなどで同じキャプチャボードを使用している場合は、そちらのキャプチャを停止してから受信します。受信データと録画は個人のバックアップとして管理してください。

## PS2側の操作

[PS2DEV・PS2SDK](https://github.com/ps2dev/ps2dev)の環境で、操作メニュー付きのELFをビルドします。

```sh
make -C ps2 SOURCE_KIND=0 INTERACTIVE=1 VIDEO_INTERLACED=1
```

出力は `ps2/ps2-video-backup.elf` です。DVDプレーヤー3.02J用の起動ディスクは[YADEのパッケージング手順](packaging/yade/README.md)を参照してください。

起動時は固定テストデータを選んだ設定画面で止まります。まず `TEST 64K` のまま、MANUAL・0.3秒・36×20で受信を確認します。コントローラーはポート1に接続します。

| ボタン | 操作 |
|---|---|
| SELECT | AUTO / MANUAL |
| 上下 | MANUALの表示時間を0.1秒刻みで変更 |
| 左右 | MANUALの密度を36×20・48×26・72×40から選択 |
| L1 / R1 | 停止中にTEST 64K・ROM0 64K・ROM0 4Mを選択 |
| START / × | 送信開始・一時停止 |

AUTOは標準密度で、周回ごとに表示時間を0.1・0.2・0.3秒へ切り替えます。PCからの応答はないため、受信品質に応じた自動調整ではありません。密度を変えると別の受信セッションになります。詳しくは[操作説明](docs/INTERACTIVE.md)を参照してください。

## PS2なしで試す

未使用のファイル名と出力先を指定します。

```sh
python -m tools.test_pattern test-data.bin
python -m tools.reference_encoder test-data.bin frames --session 0x12345678
python -m receiver --images frames --state checkpoints/test --output restored.bin
python -c "from pathlib import Path; assert Path('test-data.bin').read_bytes()==Path('restored.bin').read_bytes(); print('identical')"
python -m pytest -q
```

CとPythonの一致テストにはGCCまたはClangが必要です。コンパイラが見つからない場合、そのテストはスキップします。録画とライブ入力はCLIでも受信できます。

```sh
python -m receiver --video capture.avi --state checkpoints/video --output recovered.bin
python -m receiver --camera 0 --backend dshow --state checkpoints/live --output recovered.bin
```

## 詳細・ライセンス

[設計](ARCHITECTURE.md)、[プロトコル](PROTOCOL.md)、[実機検証手順](docs/HARDWARE.md)、[検証記録](docs/LIVE-VALIDATION-2026-10-07.md)を参照してください。圧縮、FEC、COLOR8には未対応です。

新規コードは[MIT](LICENSE)です。BIOSDrain由来の読み出し層は元の著作権表示と[MITライセンス](ps2/LICENSES/BIOSDrain-MIT.txt)を保持しています。PS2SDKなどの条件と参考実装は[参考資料](docs/REFERENCES.md)に記載しています。
