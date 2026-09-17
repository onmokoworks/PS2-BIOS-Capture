# PS2 Video Backup (PS2V)

PS2のアナログ映像から、UVCキャプチャ経由でbinaryを復元するオープンソース実験。**BIOSは同梱していません。既定ELFはBIOSを読まず、固定疑似乱数64 KiBを送信します。**

COLOR4 RAW、frame/source CRC32、周回再送、受信済みpacketの保存・再開を実装。Python referenceとPS2用portable Cはbyte/pixel単位の一致をテストします。通常のPS2SDK ELFで、FreeDVDBootへの組込みは行っていません。

実装とビルドは完了していますが、実PS2でのBIOSバックアップ成功は未検証です。状態は[検証記録](docs/VALIDATION.md)を参照してください。

## 最初に読むもの
- [設計・PS2SDK API・BIOSDrain読出し調査](ARCHITECTURE.md)
- [wire形式と画面配置](PROTOCOL.md)
- [参考実装とライセンス](docs/REFERENCES.md)
- [実機/PCSX2検証手順](docs/HARDWARE.md)

## Hostのセットアップ
Python 3.11以降。プロジェクトのルートで実行します。

```sh
python -m venv .venv
# Windows PowerShell: .venv/Scripts/Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

C/Python一致テストにはhost GCC/Clangが必要です。`CC`環境変数でコンパイラの実行ファイルを指定できます。未指定でコンパイラが見つからない場合だけC試験をskipします。Windowsではコンパイラの依存DLLがあるbinディレクトリもPATHに追加してください。

4 MiB画像往復試験は約34秒かかりました（環境依存）。短い試験だけなら `python -m pytest -q -m "not slow"`。

## BIOSなしのCLI再現
以下の入力・出力ファイル名とディレクトリは未使用のものを指定します。

```sh
python -m tools.test_pattern test-data.bin
python -m tools.reference_encoder test-data.bin frames --session 0x12345678
python -m receiver --images frames --state checkpoints/test --output restored.bin
python -c "from pathlib import Path; assert Path('test-data.bin').read_bytes()==Path('restored.bin').read_bytes(); print('identical')"
```

`tools.test_pattern`はPS2既定モードと同じxorshift32（seed=0x50533256、各更新後の下位8bit）の64 KiBを生成。任意binaryをreference encoderのinputに指定することもできます。

## 録画・UVC
```sh
python -m receiver --video capture.avi --state checkpoints/session-a --output recovered.bin
python -m receiver --camera 0 --backend dshow --state checkpoints/session-b --output recovered.bin
```

Windowsは`auto`/`dshow`/`msmf`、Linuxは`auto`/`v4l2`。カメラ番号はOpenCVのdevice indexです。640×480程度で240pを受けられるキャプチャを設定してください。現段階ではカメラの解像度・fps交渉はOpenCV/ドライバの既定設定に依存します。

同一送信sessionを再開するには同じ`--state`を指定。Ctrl+Cや動画終了までに受信した正常packetは残ります。完成前は終了コード2、完成は0、IO/整合性エラーは1、Ctrl+Cは130です。完成済みstateなら映像を開かず再出力できます（新しいoutput名を指定）。

stateは1 session専用。別のobject/起動sessionには新しいstateディレクトリを使ってください。初回のCRC合格frameからmetadataを固定し、異なるsessionを自動的に上書きしません。破損したcheckpointは起動時にエラーとして止まります。完成binaryは全体CRCが一致してから書き込み、既存outputを上書きしません。state内のpacketや録画にも元データが含まれるため、個人のバックアップとして管理してください。

## PS2SDKビルド
[公式PS2DEV](https://github.com/ps2dev/ps2dev)のEE/IOP toolchain、PS2SDK、GNU make、POSIX shell、bin2cを使用します。PS2DEV/PS2SDK/PATHは公式手順で設定します。

```sh
make -C ps2 SOURCE_KIND=0  # Phase 2: 固定64 KiB (既定)
make -C ps2 SOURCE_KIND=1  # Phase 3: ROM0先頭64 KiB
make -C ps2 SOURCE_KIND=2  # Phase 4: ROM0全4 MiB
```

出力は`ps2/ps2-video-backup.elf`。モード変更時はmain.oを必ず再コンパイルします。別名で保存したい場合は`EE_BIN=ps2v-test.elf`などを指定できます。`HOLD_VBLANKS=6`が既定、最小2。MVPでは6以上から開始してください。IOP IRXはELFへ埋め込まれるので別ファイルのロードやUSBストレージは不要です。

この成果物の`ps2/build/`には3モードのビルド済みELFとSHA256 manifestがあります。これらは未実機検証版です。まずtest ELFで撮影し、`tools.test_pattern`の出力と完全一致してからROM0の試験に進みます。ソースZIPには生成ELF・SDK・個人データを含めません。

PS2からUSBストレージ/ネットワークへ書き出す処理はありません。ELFを起動する環境自体（メモリーカード等）は別途必要です。FreeDVDBoot packagingは最後の独立工程として保留しています。

## 限界
COLOR8、圧縮、FEC、フィールド分離/高度なdeinterlace、極端なperspective、四隅を失ったcropには対応していません。各セルは8×8 pixels。毎フレーム校正しますが、compositeでの実測信頼性はまだ未確認です。RGBが潰れたり、切替途中の画面を取り込んだときはframe CRCで拒否し、次の保持画面/周回を待ちます。

4 MiBは31,776 packetsで理論約53分/周（6 VBlank保持）。実際は描画・復号・dropで長くなります。ROM1/ROM2/NVM/MECはobject typeを予約した段階です。実ROM0が安定するまで拡張しません。

## ライセンス
新規コードは[MIT](LICENSE)。BIOSDrainから変更した読出し層は元著作権表示と[MIT全文](ps2/LICENSES/BIOSDrain-MIT.txt)を保持。PS2SDKをリンクしたELFにはSDKのAFL-2.0等の条件も適用されます。参照・依存の詳細は[REFERENCES](docs/REFERENCES.md)。
