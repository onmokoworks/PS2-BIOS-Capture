# PS2 Video Backup — architecture

## 方針と境界
BIOSを含まないMITライセンスの実験プロジェクト。PS2→analog video→USB capture→PCの一方向転送。USBストレージ・ネットワークへのPS2データ出力は実装しない。起動媒体は別工程。FreeDVDBootの組込み・ISO配布は対象外。

## 構成
- `receiver/protocol.py`: 画像に依存しないwire形式、CRC、分割、検証。
- `receiver/codec.py`: COLOR4、マーカー検出、幾何補正、色校正、中心領域サンプリング。
- `receiver/store.py`: CRC合格packetの永続化、session固定、重複排除、欠落補完、最終CRC。
- `receiver/capture.py`: PNG列、OpenCV動画、UVC入力。decoderから独立。
- `tools/reference_encoder.py`: 任意binary→PNG列、実機不要。
- `ps2/`: portable C packet/renderer + GS adapter + object source + embedded read-only IOP IRX。
- `tests/`: BIOSを使わないroundtrip・劣化・誤packet・周回・永続化検証。

## データソース
objectはtype/size/read(offset,length)を提供する。TEST=0、ROM0=1。ROM1=2、ROM2=3、NVM=4、MEC=5を予約するが未実装。ROM0をEEの64-byte aligned snapshotへ取得し、全体CRCを計算後、snapshotを周回送信する。これにより送信中にsourceが変化しない。source offsetはobject内相対値。

## PS2SDK APIと実装方法
GSはSDKのgraph/draw/packet/dmaを使用。`graph_set_mode(GRAPH_MODE_NONINTERLACED, GRAPH_MODE_NTSC, GRAPH_MODE_FRAME, 0)`、`graph_set_screen`、`graph_vram_allocate`、`graph_set_framebuffer`、`graph_wait_vsync`。320×224、32-bit framebufferを二重化。`draw_setup_environment`, `draw_primitive_xyoffset`, `draw_rect_filled`, `draw_finish`, `draw_wait_finish`, `dma_channel_send_normal`で背面へ描画してVBlankで切替。アンチエイリアス、テクスチャ、ブレンドは使わない。同一packetを6 VBlank保持（約10 packets/s）。

ROM読出しは`SifInitRpc`, `SifExecModuleBuffer`, `SifBindRpc`, `SifCallRpc`。IOPは`sceSifRegisterRpc`, `sceSifSetRpcQueue`, `sceSifRpcLoop`, `sceSifSetDma`, `sceSifDmaStat`。ROM0 IOP address 0xBFC00000から4 MiB。EEへ直接ROMをmemcpyする方法には置換しない。

## BIOSDrainの詳細調査と差分
調査pin: 92aa25f0764ffde1deb77acfd5cea90db3dcb631。
`dump.c:dump_init`は64-byte aligned 0x400000 buffer、`dump_rom0_func`はhardwareInfo.ROMs[0].StartAddressから0x400000を取得する。`common_dump_func`はMEM_IO_BLOCK_SIZE単位に`SysmanSync(0)`→`SysmanReadMemory(...,1)`を実行。EE RPC clientはaligned送受信buffer、IOP handlerはROM→IOBufferのmemcpy→SIF DMA、二重bufferで重複転送を避ける。

そのまま移植しない点: 調査版のEE `SysmanReadMemory`は同期呼出し分岐が外側のif(mode)内にあり、mode=0でRPCを発行しない。IOP ReadMemory handlerは最後に発行したDMAを明示的には待たず、EEのcommon_dump_funcにも末尾Syncがない。今回の縮小版は同期RPCのみ、各DMA完了後に応答、EE cache writeback/invalidateの前後順序を明示する。IOPの範囲・サイズ・alignmentを検証し、write RPCは持たせない。ROM以外のUSB/dev9/iLink/SPU初期化とUSB/hostファイル出力は取り込まない。

BIOSDrain由来の読出し部分には元のCopyright 2022 Ty Lamontagne (Fobes)とMIT全文を維持。PS2SDKは外部ビルド依存（AFL-2.0、各ファイルの表記に従う）。GS adapterは新規実装。ZXは公開技術解説と配信app.jsを調査して思想のみ参照し、コードはコピーしない。公開GitHub repository URLは調査時404でソース一式/ライセンスを確認できなかった。FreeDVDBootもコピーしない（調査treeでroot LICENSEなし）。

## 実装順序と判定ゲート
1. Phase 1: ランダムbinary→reference PNG→decoder→byte完全一致。blur/scale/外周crop/brightness/channel shift/drop、CRC拒否、再開、4 MiBを検証。
2. Phase 2: 同一C rendererとpacket writerをhostでPythonと比較し、GSから固定PRNGデータを周回出力するELFを実装。PCSX2でGS screenshotの復号を確認、その後実機で画角/色/保持時間を調整。
3. Phase 3: ROM0先頭64 KiB snapshotの転送。IOPのRPC/DMAとキャッシュの実機検証を必須にする。
4. Phase 4: 同じ層で4 MiB、PC復元source CRC一致を確認。実機測定なしでは完成と称さない。
5. ROM0安定後のみROM1/ROM2/NVM/MEC実装、最後に独立したFreeDVDBoot packaging。

実機なし: packet/renderer/復号/保存とsynthetic試験。PCSX2: ELF起動、GS pixels、周回、emulated ROM取得の確認（自分のBIOSを別途指定）。実PS2+capture: NTSC non-interlaced受付、composite色帯域、cropping、deinterlacing、実ROMとDMA。synthetic成功は実機成功の代用にならない。

## 実施後の状態
設計後にhost MVPと3モードのPS2SDKビルドまで実施。[VALIDATION](docs/VALIDATION.md)の実測結果を正とする。Phase 3/4は実機ゲートを越えた意味での完了ではない。
